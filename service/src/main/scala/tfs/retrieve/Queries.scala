package tfs.retrieve

import io.circe.Json
import io.circe.syntax.*
import tfs.understand.Filters

/** Every request body sent to the cluster is built here, and every one carries the tenant filter.
  * TenantScopeSuite checks that no builder can leave it out.
  */
object Queries:
  def tenantFilter(tenant: String): Json = Json.obj("term" -> Json.obj("tenant" -> tenant.asJson))

  def filterClauses(tenant: String, f: Filters): List[Json] =
    val price =
      if f.minPrice.isEmpty && f.maxPrice.isEmpty then None
      else
        val bounds = f.minPrice.map(v => "gte" -> v.asJson).toList ++ f.maxPrice.map(v => "lte" -> v.asJson).toList
        Some(Json.obj("range" -> Json.obj("price" -> Json.fromFields(bounds))))
    List(tenantFilter(tenant)) ++
      f.colour.map(v => term("colour", v.asJson)).toList ++
      f.brand.map(v => term("brand", v.asJson)).toList ++
      f.size.map(v => term("size", v.asJson)).toList ++
      f.inStock.map(v => term("inStock", v.asJson)).toList ++
      price.toList

  private def term(field: String, value: Json): Json = Json.obj("term" -> Json.obj(field -> value))

  def sku(tenant: String, sku: String, size: Int): Json =
    Json.obj(
      "size" -> size.asJson,
      "_source" -> false.asJson,
      "query" -> Json.obj("bool" -> Json.obj("filter" -> Json.arr(tenantFilter(tenant), term("sku", sku.asJson))))
    )

  def lexical(tenant: String, text: String, filters: Filters, fields: List[String], size: Int): Json =
    val must =
      if text.trim.isEmpty then Json.obj("match_all" -> Json.obj())
      else Json.obj("multi_match" -> Json.obj("query" -> text.asJson, "fields" -> fields.asJson))
    Json.obj(
      "size" -> size.asJson,
      "_source" -> false.asJson,
      "query" -> Json.obj(
        "bool" -> Json.obj("must" -> Json.arr(must), "filter" -> filterClauses(tenant, filters).asJson)
      )
    )

  def knn(tenant: String, vector: Vector[Double], filters: Filters, size: Int, numCandidates: Int): Json =
    Json.obj(
      "size" -> size.asJson,
      "_source" -> false.asJson,
      "knn" -> Json.obj(
        "field" -> "vec".asJson,
        "query_vector" -> vector.asJson,
        "k" -> size.asJson,
        "num_candidates" -> numCandidates.asJson,
        "filter" -> filterClauses(tenant, filters).asJson
      )
    )

  def facets(tenant: String): Json =
    def agg(field: String) = Json.obj("terms" -> Json.obj("field" -> field.asJson, "size" -> 500.asJson))
    Json.obj(
      "size" -> 0.asJson,
      "query" -> Json.obj("bool" -> Json.obj("filter" -> Json.arr(tenantFilter(tenant)))),
      "aggs" -> Json.obj("colour" -> agg("colour"), "brand" -> agg("brand"), "size" -> agg("size"))
    )

  def clearTenant(tenant: String): Json =
    Json.obj("query" -> Json.obj("bool" -> Json.obj("filter" -> Json.arr(tenantFilter(tenant)))))
