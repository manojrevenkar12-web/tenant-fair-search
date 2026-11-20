package tfs.retrieve

import tfs.config.{Design, Weights}
import tfs.understand.{Filters, Parsed, Shape}

/** What one search will do. Code decides it from the design and the parsed query; nothing here calls the cluster. */
final case class Plan(
    label: String,
    skuExact: Boolean,
    lexical: Boolean,
    semantic: Boolean,
    text: String,
    filters: Filters,
    weights: Weights
)

object Router:
  private val even = Weights(1.0, 1.0)

  /** @param raw the text as sent
    * @param explicit the constraints the client sent as fields (agents do)
    * @param hasVector whether the tenant's term model knows any word of the text
    */
  def plan(
      design: Design,
      parsed: Parsed,
      raw: String,
      explicit: Filters,
      hasVector: Boolean,
      weights: Map[String, Weights]
  ): Plan =
    val filters = if design.understand then explicit.orElse(parsed.extracted) else explicit
    val text = if design.understand then parsed.text else raw.trim
    if !design.route then
      Plan(label(design.lexical, design.semantic), false, design.lexical, design.semantic, text, filters, even)
    else
      parsed.shape match
        case Shape.Sku =>
          Plan("sku", true, true, false, raw.trim, Filters(), even)
        case shape =>
          val semantic = design.semantic && hasVector
          val lexical = design.lexical || !semantic
          val w = if lexical && semantic then weights.getOrElse(shape.toString.toLowerCase, even) else even
          Plan(label(lexical, semantic), false, lexical, semantic, text, filters, w)

  private def label(lexical: Boolean, semantic: Boolean): String =
    (lexical, semantic) match
      case (true, true)   => "hybrid"
      case (true, false)  => "lexical"
      case (false, true)  => "semantic"
      case (false, false) => "none"

object Fusion:
  /** Weighted reciprocal rank fusion; ties broken by id so the same lists always give the same order. */
  def rrf(lists: List[(Vector[String], Double)], rankConstant: Int, top: Int): Vector[(String, Double)] =
    val scores = scala.collection.mutable.HashMap.empty[String, Double]
    lists.foreach { case (ids, weight) =>
      ids.zipWithIndex.foreach { case (id, i) =>
        scores.update(id, scores.getOrElse(id, 0.0) + weight / (rankConstant + i + 1).toDouble)
      }
    }
    scores.toVector.sortBy { case (id, s) => (-s, id) }.take(top)
