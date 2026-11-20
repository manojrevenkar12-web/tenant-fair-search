package tfs.config

import cats.effect.IO
import io.circe.{Decoder, Json}
import io.circe.generic.semiauto.deriveDecoder
import io.circe.parser.{decode, parse}

import java.nio.charset.StandardCharsets
import java.nio.file.{Files, Path, Paths}

/** Every setting the service reads. The values live in config/platform.json, which the evaluation reads too. */
final case class ServiceSettings(
    port: Int,
    esUrl: String,
    index: String,
    modelDir: String,
    requestTimeoutMs: Long,
    evalOverrides: Boolean,
    tenantPattern: String,
    maxBulk: Int
)

final case class TextSettings(tokenPattern: String, minTokenLength: Int, stopwords: List[String])

final case class UnderstandingSettings(
    skuPattern: String,
    sentenceMinTokens: Int,
    maxPriceWords: List[String],
    minPriceWords: List[String],
    currencyWords: List[String],
    inStockPhrases: List[String],
    sizeWords: List[String],
    colourSynonyms: Map[String, String]
)

final case class Weights(lexical: Double, semantic: Double)

final case class RetrievalSettings(
    k: Int,
    candidates: Int,
    knnNumCandidates: Int,
    rrfRankConstant: Int,
    lexicalFields: List[String],
    defaultDesign: String,
    weights: Map[String, Weights]
)

/** A design is a set of switches; the evaluation compares every design on the same queries. */
final case class Design(lexical: Boolean, semantic: Boolean, understand: Boolean, route: Boolean)

final case class AdmissionSettings(
    mode: String,
    globalConcurrency: Int,
    tenantShare: Double,
    ratePerSecond: Double,
    burst: Double
):
  /** The most requests one tenant may have inside the cluster at once. */
  def tenantCap: Int = math.max(1, math.floor(globalConcurrency * tenantShare).toInt)

final case class EmbeddingSettings(dim: Int)

final case class CostSettings(nodeEurPerHour: Double, nodeConcurrency: Int):
  /** Euro for one millisecond of one search slot on a node. */
  def eurPerSlotMs: Double = nodeEurPerHour / 3600000.0 / nodeConcurrency.toDouble

final case class Platform(
    service: ServiceSettings,
    text: TextSettings,
    understanding: UnderstandingSettings,
    retrieval: RetrievalSettings,
    designs: Map[String, Design],
    admission: AdmissionSettings,
    embedding: EmbeddingSettings,
    cost: CostSettings
)

object Platform:
  given Decoder[ServiceSettings] = deriveDecoder
  given Decoder[TextSettings] = deriveDecoder
  given Decoder[UnderstandingSettings] = deriveDecoder
  given Decoder[Weights] = deriveDecoder
  given Decoder[RetrievalSettings] = deriveDecoder
  given Decoder[Design] = deriveDecoder
  given Decoder[AdmissionSettings] = deriveDecoder
  given Decoder[EmbeddingSettings] = deriveDecoder
  given Decoder[CostSettings] = deriveDecoder
  given Decoder[Platform] = deriveDecoder

  /** The repository root: the nearest folder upwards that holds config/platform.json. */
  def root: Path =
    var dir = Paths.get("").toAbsolutePath
    while dir != null && !Files.exists(dir.resolve("config/platform.json")) do dir = dir.getParent
    if dir == null then Paths.get("").toAbsolutePath else dir

  def read(path: Path): String = new String(Files.readAllBytes(path), StandardCharsets.UTF_8)

  def fromString(text: String): Either[Throwable, Platform] = decode[Platform](text)

  /** Reads config/platform.json (or TFS_CONFIG); TFS_EVAL_OVERRIDES and TFS_ES_URL may switch the evaluation on. */
  def load: IO[Platform] = IO.blocking {
    val path = sys.env.get("TFS_CONFIG").map(Paths.get(_)).getOrElse(root.resolve("config/platform.json"))
    val base = fromString(read(path)).fold(e => throw e, identity)
    val overrides = sys.env.get("TFS_EVAL_OVERRIDES").contains("true")
    val esUrl = sys.env.getOrElse("TFS_ES_URL", base.service.esUrl)
    val modelDir = sys.env.getOrElse("TFS_MODEL_DIR", root.resolve(base.service.modelDir).toString)
    base.copy(service = base.service.copy(evalOverrides = base.service.evalOverrides || overrides, esUrl = esUrl, modelDir = modelDir))
  }

  /** The index settings and mapping from config/index.json. */
  def indexMapping: IO[Json] = IO.blocking(parse(read(root.resolve("config/index.json"))).fold(e => throw e, identity))
