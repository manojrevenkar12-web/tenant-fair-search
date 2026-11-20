package tfs.es

import cats.effect.IO
import io.circe.Json
import io.circe.syntax.*
import org.http4s.{MediaType, Method, Request, Status, Uri}
import org.http4s.circe.*
import org.http4s.client.Client
import org.http4s.headers.`Content-Type`

/** A hit list as the cluster returned it, with the milliseconds the cluster says it spent. */
final case class Hits(ids: Vector[String], took: Long)

/** The only code that talks to Elasticsearch. Documents are routed and stored by tenant. */
final class Es(client: Client[IO], base: Uri, index: String):
  private val ndjson = `Content-Type`(MediaType.unsafeParse("application/x-ndjson"))

  def docId(tenant: String, id: String): String = s"$tenant:$id"

  def ensureIndex(mapping: Json): IO[Unit] =
    client.status(Request[IO](Method.HEAD, base / index)).flatMap {
      case Status.Ok => IO.unit
      case _         => client.expect[Json](Request[IO](Method.PUT, base / index).withEntity(mapping)).void
    }

  def search(tenant: String, body: Json): IO[Hits] =
    val uri = (base / index / "_search").withQueryParam("routing", tenant)
    client.expect[Json](Request[IO](Method.POST, uri).withEntity(body)).map { json =>
      val prefix = s"$tenant:"
      val ids = json.hcursor
        .downField("hits")
        .downField("hits")
        .as[List[Json]]
        .getOrElse(Nil)
        .flatMap(_.hcursor.get[String]("_id").toOption)
        .map(id => if id.startsWith(prefix) then id.drop(prefix.length) else id)
        .toVector
      Hits(ids, json.hcursor.get[Long]("took").getOrElse(0L))
    }

  def aggregate(tenant: String, body: Json): IO[Json] =
    val uri = (base / index / "_search").withQueryParam("routing", tenant)
    client.expect[Json](Request[IO](Method.POST, uri).withEntity(body))

  /** Bulk-indexes documents and refreshes, so the next search sees them. Fails if any item failed. */
  def bulk(tenant: String, docs: Vector[(String, Json)]): IO[Int] =
    if docs.isEmpty then IO.pure(0)
    else
      val lines = docs.flatMap { case (id, doc) =>
        val action = Json.obj(
          "index" -> Json.obj(
            "_index" -> index.asJson,
            "_id" -> docId(tenant, id).asJson,
            "routing" -> tenant.asJson
          )
        )
        Vector(action.noSpaces, doc.noSpaces)
      }
      val body = lines.mkString("", "\n", "\n")
      val uri = (base / "_bulk").withQueryParam("refresh", "wait_for")
      client.expect[Json](Request[IO](Method.POST, uri).withEntity(body).withContentType(ndjson)).flatMap { json =>
        if json.hcursor.get[Boolean]("errors").getOrElse(true) then
          IO.raiseError(new IllegalStateException(s"bulk indexing failed: ${json.noSpaces.take(500)}"))
        else IO.pure(docs.size)
      }

  def clear(tenant: String, body: Json): IO[Unit] =
    val uri = (base / index / "_delete_by_query")
      .withQueryParam("routing", tenant)
      .withQueryParam("refresh", "true")
      .withQueryParam("conflicts", "proceed")
    client.expect[Json](Request[IO](Method.POST, uri).withEntity(body)).void
