package tfs.text

import tfs.config.TextSettings

import java.util.Locale
import scala.util.matching.Regex

/** The one tokenizer rule. The Python trainer applies the same pattern, stopwords and minimum length from
  * config/platform.json, and tests/fixtures/tokenize.json is checked by both test suites.
  */
final class Tokenizer(settings: TextSettings):
  private val pattern: Regex = settings.tokenPattern.r
  private val stop: Set[String] = settings.stopwords.toSet

  def apply(text: String): Vector[String] =
    pattern
      .findAllIn(text.toLowerCase(Locale.ROOT))
      .filter(t => t.length >= settings.minTokenLength && !stop.contains(t))
      .toVector
