package tfs.http

import cats.effect.{IO, Ref}
import cats.syntax.all.*
import io.circe.{Decoder, Encoder, Json}
import io.circe.generic.semiauto.{deriveDecoder, deriveEncoder}
import io.circe.syntax.*
import tfs.config.{Design, Platform}
import tfs.es.Es
import tfs.retrieve.{Fusion, Plan, Queries, Router}
import tfs.text.{Models, Tokenizer}
import tfs.understand.{Facets, Filters, Parser, Shape}

final case class Product(
    id: String,
    sku: String,
    title: String,
    description: String,
    brand: String,
    colour: String,
    size: String,
    price: Double,
    inStock: Boolean
)

object Product:
  given Decoder[Product] = deriveDecoder

/** A search request. Shoppers send `query`; agents may also send `filters` as fields. */
final case class SearchRequest(query: String, filters: Option[Filters], k: Option[Int])

object SearchRequest:
  given Decoder[SearchRequest] = deriveDecoder

final case class Hit(id: String, score: Double)

object Hit:
  given Encoder[Hit] = deriveEncoder

final case class SearchResponse(
    tenant: String,
    design: String,
    shape: Shape,
    plan: String,
    text: String,
    filters: Filters,
    hits: Vector[Hit],
    esTookMs: Long,
    costEur: Double
)

object SearchResponse:
  given Encoder[SearchResponse] = deriveEncoder

final class SearchService(
    platform: Platform,
    es: Es,
    models: Models,
    tokenizer: Tokenizer,
    parser: Parser,
    facets: Ref[IO, Map[String, Facets]]
):
  private val r = platform.retrieval

  def design(name: String): Option[Design] = platform.designs.get(name)

  def index(tenant: String, products: List[Product]): IO[Int] =
    models.forget(tenant) >> facets.update(_ - tenant) >> models.forTenant(tenant).flatMap { model =>
      val docs = products.toVector.map { p =>
        val vector = model.flatMap(_.embed(tokenizer(p.title + " " + p.description)))
        val fields = List(
          "tenant" -> tenant.asJson,
          "id" -> p.id.asJson,
          "sku" -> p.sku.asJson,
          "title" -> p.title.asJson,
          "description" -> p.description.asJson,
          "brand" -> p.brand.asJson,
          "colour" -> p.colour.asJson,
          "size" -> p.size.asJson,
          "price" -> p.price.asJson,
          "inStock" -> p.inStock.asJson
        ) ++ vector.map(v => "vec" -> v.asJson).toList
        p.id -> Json.fromFields(fields)
      }
      docs.grouped(1000).toList.traverse(batch => es.bulk(tenant, batch)).map(_.sum)
    }

  def clear(tenant: String): IO[Unit] =
    es.clear(tenant, Queries.clearTenant(tenant)) >> facets.update(_ - tenant) >> models.forget(tenant)

  def facetsOf(tenant: String): IO[Facets] =
    facets.get.map(_.get(tenant)).flatMap {
      case Some(f) => IO.pure(f)
      case None =>
        es.aggregate(tenant, Queries.facets(tenant)).flatMap { json =>
          def keys(name: String): Set[String] =
            json.hcursor
              .downField("aggregations")
              .downField(name)
              .downField("buckets")
              .as[List[Json]]
              .getOrElse(Nil)
              .flatMap(_.hcursor.get[String]("key").toOption)
              .toSet
          val f = Facets(keys("colour"), keys("brand"), keys("size"))
          facets.update(_.updated(tenant, f)).as(f)
        }
    }

  def search(tenant: String, designName: String, req: SearchRequest): IO[SearchResponse] =
    val d = platform.designs(designName)
    val explicit = req.filters.getOrElse(Filters())
    val k = req.k.getOrElse(r.k).max(1).min(r.candidates)
    for
      f <- if d.understand then facetsOf(tenant) else IO.pure(Facets.empty)
      model <- models.forTenant(tenant)
      parsed = parser.parse(req.query, req.filters.isDefined, f)
      semanticText = if d.understand then parsed.text else req.query
      vector = model.flatMap(_.embed(tokenizer(semanticText)))
      plan = Router.plan(d, parsed, req.query, explicit, vector.isDefined, r.weights)
      result <- execute(tenant, plan, vector, k)
    yield
      val (hits, took) = result
      SearchResponse(
        tenant,
        designName,
        parsed.shape,
        plan.label,
        plan.text,
        plan.filters,
        hits,
        took,
        took.toDouble * platform.cost.eurPerSlotMs
      )

  private def execute(tenant: String, plan: Plan, vector: Option[Vector[Double]], k: Int): IO[(Vector[Hit], Long)] =
    val n = r.candidates
    val lexicalIO =
      if plan.lexical then es.search(tenant, Queries.lexical(tenant, plan.text, plan.filters, r.lexicalFields, n)).map(Some(_))
      else IO.pure(None)
    val semanticIO = vector match
      case Some(v) if plan.semantic =>
        es.search(tenant, Queries.knn(tenant, v, plan.filters, n, r.knnNumCandidates)).map(Some(_))
      case _ => IO.pure(None)
    val ranked =
      (lexicalIO, semanticIO).parTupled.map { case (lex, sem) =>
        val lists = lex.map(h => (h.ids, plan.weights.lexical)).toList ++ sem.map(h => (h.ids, plan.weights.semantic)).toList
        val took = lex.map(_.took).getOrElse(0L) + sem.map(_.took).getOrElse(0L)
        val fused = lists match
          case Nil                => Vector.empty
          case (ids, _) :: Nil    => ids.take(k).zipWithIndex.map { case (id, i) => (id, 1.0 / (r.rrfRankConstant + i + 1)) }
          case several            => Fusion.rrf(several, r.rrfRankConstant, k)
        (fused.map { case (id, s) => Hit(id, s) }, took)
      }
    if plan.skuExact then
      es.search(tenant, Queries.sku(tenant, plan.text, k)).flatMap { exact =>
        if exact.ids.nonEmpty then IO.pure((exact.ids.map(Hit(_, 1.0)), exact.took))
        else ranked.map { case (hits, took) => (hits, took + exact.took) }
      }
    else ranked
