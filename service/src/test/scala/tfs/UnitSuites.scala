package tfs

import io.circe.Json
import io.circe.parser.parse
import tfs.config.{AdmissionSettings, Design, Platform, Weights}
import tfs.retrieve.{Fusion, Queries, Router}
import tfs.tenancy.Bucket
import tfs.text.{Embedder, TermModel, Tokenizer}
import tfs.understand.{Facets, Filters, Parser, Shape}

object Fixtures:
  lazy val platform: Platform =
    Platform.fromString(Platform.read(Platform.root.resolve("config/platform.json"))).fold(e => throw e, identity)
  lazy val tokenizer: Tokenizer = Tokenizer(platform.text)
  lazy val parser: Parser = Parser(platform.understanding, tokenizer)
  val facets: Facets = Facets(Set("navy", "black", "red", "dark green"), Set("nordkamm", "vela"), Set("m", "l", "42"))

class TokenizerSuite extends munit.FunSuite:
  test("the Scala tokenizer gives the shared fixture's tokens (the Python trainer checks the same file)") {
    val cases = parse(Platform.read(Platform.root.resolve("tests/fixtures/tokenize.json"))).toOption.get.asArray.get
    assert(cases.nonEmpty)
    cases.foreach { c =>
      val text = c.hcursor.get[String]("text").toOption.get
      val expected = c.hcursor.get[Vector[String]]("tokens").toOption.get
      assertEquals(Fixtures.tokenizer(text), expected, text)
    }
  }

class ParserSuite extends munit.FunSuite:
  import Fixtures.*

  test("shapes: SKU, keyword, sentence, agent") {
    assertEquals(parser.shapeOf("AB-10234", structured = false), Shape.Sku)
    assertEquals(parser.shapeOf("navy jacket", structured = false), Shape.Keyword)
    assertEquals(parser.shapeOf("warm waterproof jacket for winter hiking trips", structured = false), Shape.Sentence)
    assertEquals(parser.shapeOf("navy jacket", structured = true), Shape.Agent)
  }

  test("a sentence gives up its price, colour, brand, size and stock constraints, and the rest is left to match") {
    val p = parser.parse("I need a dark blue Nordkamm rain jacket size M under 120 euros, in stock", false, facets)
    assertEquals(p.shape, Shape.Sentence)
    assertEquals(p.extracted.maxPrice, Some(120.0))
    assertEquals(p.extracted.colour, Some("navy"))
    assertEquals(p.extracted.brand, Some("nordkamm"))
    assertEquals(p.extracted.size, Some("m"))
    assertEquals(p.extracted.inStock, Some(true))
    assert(!p.text.contains("120"), p.text)
    assert(p.text.contains("rain jacket"), p.text)
  }

  test("only the tenant's own facet values become filters") {
    val p = parser.parse("purple jacket from vela over 40 €", false, facets)
    assertEquals(p.extracted.colour, None)
    assertEquals(p.extracted.brand, Some("vela"))
    assertEquals(p.extracted.minPrice, Some(40.0))
  }

  test("multi-word facet values win over shorter ones") {
    assertEquals(parser.parse("dark green fleece", false, facets).extracted.colour, Some("dark green"))
  }

  test("explicit agent filters win over extracted ones") {
    val explicit = Filters(maxPrice = Some(50.0))
    val merged = explicit.orElse(Filters(maxPrice = Some(120.0), colour = Some("navy")))
    assertEquals(merged, Filters(colour = Some("navy"), maxPrice = Some(50.0)))
  }

class RouterSuite extends munit.FunSuite:
  import Fixtures.*
  private val routed = platform.designs("routed")
  private val weights = platform.retrieval.weights

  test("a SKU goes to the exact lookup and skips the vector search") {
    val p = parser.parse("AB-10234", false, facets)
    val plan = Router.plan(routed, p, "AB-10234", Filters(), hasVector = true, weights)
    assert(plan.skuExact)
    assert(!plan.semantic)
  }

  test("a query the term model cannot embed falls back to lexical") {
    val p = parser.parse("zzqx", false, facets)
    val plan = Router.plan(routed, p, "zzqx", Filters(), hasVector = false, weights)
    assertEquals(plan.label, "lexical")
  }

  test("a sentence is fused with the sentence weights") {
    val raw = "warm waterproof jacket for winter hiking under 100"
    val plan = Router.plan(routed, parser.parse(raw, false, facets), raw, Filters(), hasVector = true, weights)
    assertEquals(plan.label, "hybrid")
    assertEquals(plan.weights, weights("sentence"))
    assertEquals(plan.filters.maxPrice, Some(100.0))
  }

  test("without understanding, the raw text is searched and only explicit filters apply") {
    val raw = "navy jacket under 100"
    val d = Design(lexical = true, semantic = true, understand = false, route = false)
    val plan = Router.plan(d, parser.parse(raw, false, facets), raw, Filters(), hasVector = true, weights)
    assertEquals(plan.text, raw)
    assert(plan.filters.isEmpty)
    assertEquals(plan.weights, Weights(1.0, 1.0))
  }

class FusionSuite extends munit.FunSuite:
  test("reciprocal rank fusion rewards agreement and breaks ties by id") {
    val fused = Fusion.rrf(List((Vector("a", "b", "c"), 1.0), (Vector("c", "a", "d"), 1.0)), 60, 3)
    assertEquals(fused.map(_._1), Vector("a", "c", "b"))
    val tie = Fusion.rrf(List((Vector("y"), 1.0), (Vector("x"), 1.0)), 60, 2)
    assertEquals(tie.map(_._1), Vector("x", "y"))
  }

  test("weights move a list up") {
    val fused = Fusion.rrf(List((Vector("lex"), 0.5), (Vector("sem"), 1.0)), 60, 2)
    assertEquals(fused.head._1, "sem")
  }

class TenantScopeSuite extends munit.FunSuite:
  private val tenant = "shop-a"
  private def hasTenant(json: Json): Boolean = json.noSpaces.contains("""{"term":{"tenant":"shop-a"}}""")

  test("every query the service can send to the cluster carries the tenant filter") {
    val f = Filters(colour = Some("navy"), minPrice = Some(10.0), maxPrice = Some(20.0), inStock = Some(true))
    val bodies = List(
      Queries.sku(tenant, "ab-1234", 10),
      Queries.lexical(tenant, "jacket", f, List("title"), 10),
      Queries.lexical(tenant, "", Filters(), List("title"), 10),
      Queries.knn(tenant, Vector(1.0, 0.0), f, 10, 100),
      Queries.facets(tenant),
      Queries.clearTenant(tenant)
    )
    bodies.foreach(b => assert(hasTenant(b), b.noSpaces))
  }

  test("a price range has both bounds") {
    val clauses = Queries.filterClauses(tenant, Filters(minPrice = Some(10.0), maxPrice = Some(20.0)))
    assert(clauses.exists(_.noSpaces == """{"range":{"price":{"gte":10.0,"lte":20.0}}}"""), clauses.map(_.noSpaces))
  }

class EmbedderSuite extends munit.FunSuite:
  private val model = TermModel("t", 2, Map("rain" -> 2.0), Map("rain" -> Vector(1.0, 0.0), "jacket" -> Vector(0.0, 1.0)))

  test("unknown words give no vector; known words give a unit vector weighted by idf") {
    val e = Embedder(model)
    assertEquals(e.embed(Vector("zzz")), None)
    val v = e.embed(Vector("rain", "jacket")).get
    assertEqualsDouble(math.sqrt(v.map(x => x * x).sum), 1.0, 1e-9)
    assert(v(0) > v(1))
  }

class BucketSuite extends munit.FunSuite:
  test("a bucket allows its burst, then its rate") {
    val rate = 10.0
    val burst = 3.0
    var b: Option[Bucket] = None
    val first = (1 to 4).map { _ =>
      val (next, ok) = Bucket.take(b, 0L, rate, burst)
      b = Some(next)
      ok
    }
    assertEquals(first, Vector(true, true, true, false))
    val (_, afterTenth) = Bucket.take(b, 100000000L, rate, burst)
    assert(afterTenth)
  }

  test("retry-after is at least one second") {
    assertEquals(Bucket.retryAfterSeconds(Bucket(0.5, 0L), 40.0), 1)
  }

  test("one tenant holds at most its share of the cluster's slots") {
    assertEquals(AdmissionSettings("fair", 8, 0.375, 40.0, 80.0).tenantCap, 3)
    assertEquals(AdmissionSettings("fair", 2, 0.1, 40.0, 80.0).tenantCap, 1)
  }
