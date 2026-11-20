package tfs.understand

import io.circe.{Decoder, Encoder}
import io.circe.generic.semiauto.{deriveDecoder, deriveEncoder}
import tfs.config.UnderstandingSettings
import tfs.text.Tokenizer

import java.util.Locale
import java.util.regex.Pattern
import scala.util.matching.Regex

/** Hard constraints. An agent sends them explicitly; a shopper's sentence may contain them. */
final case class Filters(
    colour: Option[String] = None,
    brand: Option[String] = None,
    size: Option[String] = None,
    minPrice: Option[Double] = None,
    maxPrice: Option[Double] = None,
    inStock: Option[Boolean] = None
):
  /** Explicit values win; extracted values only fill what is missing. */
  def orElse(other: Filters): Filters = Filters(
    colour.orElse(other.colour),
    brand.orElse(other.brand),
    size.orElse(other.size),
    minPrice.orElse(other.minPrice),
    maxPrice.orElse(other.maxPrice),
    inStock.orElse(other.inStock)
  )

  def isEmpty: Boolean = this == Filters()

object Filters:
  given Decoder[Filters] = deriveDecoder
  given Encoder[Filters] = deriveEncoder

enum Shape:
  case Sku, Keyword, Sentence, Agent

object Shape:
  given Encoder[Shape] = Encoder.encodeString.contramap(_.toString.toLowerCase(Locale.ROOT))

/** What the tenant's catalogue can be filtered on, read from the index. */
final case class Facets(colours: Set[String], brands: Set[String], sizes: Set[String])

object Facets:
  val empty: Facets = Facets(Set.empty, Set.empty, Set.empty)

/** The query as the service understood it: its shape, the text left to match, and the constraints found in it. */
final case class Parsed(shape: Shape, text: String, extracted: Filters)

/** Rules, not a model: what is extracted is only what the tenant's own facets and config/platform.json allow. */
final class Parser(settings: UnderstandingSettings, tokenizer: Tokenizer):
  private val sku: Regex = settings.skuPattern.r
  private def alternatives(words: List[String]): String =
    words.sortBy(-_.length).map(w => Pattern.quote(w)).mkString("|")
  private val currency = alternatives(settings.currencyWords)
  private def priceRegex(words: List[String]): Regex =
    (s"\\b(?:${alternatives(words)})\\s+(?:€\\s*)?(\\d+(?:[.,]\\d+)?)\\s*(?:€|(?:$currency)\\b)?").r
  private val maxPrice = priceRegex(settings.maxPriceWords)
  private val minPrice = priceRegex(settings.minPriceWords)
  private val sizeRegex: Regex = s"\\b(?:${alternatives(settings.sizeWords)})\\s+([a-z0-9]+)\\b".r

  def shapeOf(text: String, structured: Boolean): Shape =
    val trimmed = text.trim.toLowerCase(Locale.ROOT)
    if structured then Shape.Agent
    else if sku.matches(trimmed) then Shape.Sku
    else if tokenizer(trimmed).size >= settings.sentenceMinTokens then Shape.Sentence
    else Shape.Keyword

  def parse(text: String, structured: Boolean, facets: Facets): Parsed =
    val shape = shapeOf(text, structured)
    if shape == Shape.Sku then Parsed(shape, text.trim.toLowerCase(Locale.ROOT), Filters())
    else
      var rest = " " + normalise(text) + " "
      def number(s: String): Double = s.replace(',', '.').toDouble

      val max = maxPrice.findFirstMatchIn(rest).map(m => number(m.group(1)))
      rest = maxPrice.replaceAllIn(rest, " ")
      val min = minPrice.findFirstMatchIn(rest).map(m => number(m.group(1)))
      rest = minPrice.replaceAllIn(rest, " ")

      val size = sizeRegex.findFirstMatchIn(rest).map(_.group(1)).filter(facets.sizes.contains)
      if size.isDefined then rest = sizeRegex.replaceAllIn(rest, " ")

      val inStock = settings.inStockPhrases.find(p => containsPhrase(rest, p))
      inStock.foreach(p => rest = removePhrase(rest, p))

      val colour = longestPhrase(rest, facets.colours)
      colour.foreach(c => rest = removePhrase(rest, c))
      val brand = longestPhrase(rest, facets.brands)
      brand.foreach(b => rest = removePhrase(rest, b))

      val filters = Filters(colour, brand, size, min, max, inStock.map(_ => true))
      Parsed(shape, rest.trim.replaceAll("\\s+", " "), filters)

  /** Lower case, the currency sign spaced out, and colour synonyms mapped to the tenant's words. */
  def normalise(text: String): String =
    val lower = text.toLowerCase(Locale.ROOT).replace("€", " € ")
    settings.colourSynonyms.toList.sortBy(-_._1.length).foldLeft(lower) { case (acc, (from, to)) =>
      acc.replaceAll(s"\\b${Pattern.quote(from)}\\b", to)
    }

  private def containsPhrase(text: String, phrase: String): Boolean =
    s"\\b${Pattern.quote(phrase)}\\b".r.findFirstIn(text).isDefined

  private def removePhrase(text: String, phrase: String): String =
    text.replaceAll(s"\\b${Pattern.quote(phrase)}\\b", " ")

  private def longestPhrase(text: String, candidates: Set[String]): Option[String] =
    candidates.toList.sortBy(c => (-c.length, c)).find(c => containsPhrase(text, c))
