package tfs.text

import cats.effect.{IO, Ref}
import io.circe.Decoder
import io.circe.generic.semiauto.deriveDecoder
import io.circe.parser.decode

import java.nio.file.{Files, Path}

/** One tenant's term vectors, learned offline from that tenant's own search-to-purchase logs. */
final case class TermModel(tenant: String, dim: Int, idf: Map[String, Double], terms: Map[String, Vector[Double]])

object TermModel:
  given Decoder[TermModel] = deriveDecoder

/** Text to a unit vector: the idf-weighted mean of the known terms' vectors. None when no term is known. */
final class Embedder(model: TermModel):
  def dim: Int = model.dim

  def knows(token: String): Boolean = model.terms.contains(token)

  def embed(tokens: Seq[String]): Option[Vector[Double]] =
    val acc = Array.fill(model.dim)(0.0)
    var seen = false
    tokens.foreach { t =>
      model.terms.get(t).foreach { v =>
        val w = model.idf.getOrElse(t, 1.0)
        var i = 0
        while i < model.dim do
          acc(i) += w * v(i)
          i += 1
        seen = true
      }
    }
    val norm = math.sqrt(acc.map(x => x * x).sum)
    if !seen || norm == 0.0 then None else Some(acc.map(_ / norm).toVector)

/** Term models by tenant, read from the model folder on first use and dropped when the tenant re-indexes. */
final class Models(dir: Path, cache: Ref[IO, Map[String, Embedder]]):
  def forTenant(tenant: String): IO[Option[Embedder]] =
    cache.get.map(_.get(tenant)).flatMap[Option[Embedder]] {
      case some @ Some(_) => IO.pure(some)
      case None =>
        val file = dir.resolve(s"$tenant.json")
        IO.blocking(Files.exists(file)).flatMap[Option[Embedder]] {
          case false => IO.pure(None)
          case true =>
            IO.blocking(new String(Files.readAllBytes(file), "UTF-8"))
              .flatMap(text => IO.fromEither(decode[TermModel](text)))
              .map(Embedder(_))
              .flatMap(e => cache.update(_.updated(tenant, e)).as(Option(e)))
        }
    }

  def forget(tenant: String): IO[Unit] = cache.update(_ - tenant)

object Models:
  def apply(dir: Path): IO[Models] = Ref.of[IO, Map[String, Embedder]](Map.empty).map(new Models(dir, _))
