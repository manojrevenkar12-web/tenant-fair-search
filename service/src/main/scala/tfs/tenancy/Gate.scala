package tfs.tenancy

import cats.effect.{IO, Ref}
import cats.effect.std.Semaphore
import io.circe.Encoder
import io.circe.generic.semiauto.deriveEncoder
import tfs.config.AdmissionSettings

/** A token bucket: `rate` requests a second on average, up to `burst` at once. */
final case class Bucket(tokens: Double, lastNanos: Long)

object Bucket:
  def take(previous: Option[Bucket], now: Long, rate: Double, burst: Double): (Bucket, Boolean) =
    val current = previous.getOrElse(Bucket(burst, now))
    val elapsed = math.max(0L, now - current.lastNanos).toDouble / 1e9
    val refilled = math.min(burst, current.tokens + elapsed * rate)
    if refilled >= 1.0 then (Bucket(refilled - 1.0, now), true) else (Bucket(refilled, now), false)

  def retryAfterSeconds(bucket: Bucket, rate: Double): Int =
    math.max(1, math.ceil((1.0 - bucket.tokens) / rate).toInt)

enum Outcome[+A]:
  case Done(value: A)
  case Limited(retryAfterSeconds: Int)

final case class Counts(admitted: Long, limited: Long, timedOut: Long)

object Counts:
  val zero: Counts = Counts(0, 0, 0)
  given Encoder[Counts] = deriveEncoder

/** Admission in front of the cluster.
  *
  * "fair": each tenant's rate is shaped by its own bucket, and one tenant may hold at most `tenantCap` of the
  * cluster's `globalConcurrency` search slots, so a burst from one shop (or one shop's AI agent) queues behind
  * itself and not in front of the others.
  *
  * "none": one shared queue in arrival order; the evaluation's baseline.
  */
final class Gate private (
    settings: AdmissionSettings,
    global: Semaphore[IO],
    slots: Ref[IO, Map[String, Semaphore[IO]]],
    buckets: Ref[IO, Map[String, Bucket]],
    counts: Ref[IO, Map[String, Counts]]
):
  def run[A](tenant: String, mode: String)(work: IO[A]): IO[Outcome[A]] =
    if mode == "none" then count(tenant, _.copy(admitted = 1)) >> global.permit.use(_ => work).map(Outcome.Done(_))
    else
      IO.monotonic.map(_.toNanos).flatMap { now =>
        buckets
          .modify { m =>
            val (b, ok) = Bucket.take(m.get(tenant), now, settings.ratePerSecond, settings.burst)
            (m.updated(tenant, b), (b, ok))
          }
          .flatMap[Outcome[A]] {
            case (bucket, false) =>
              count(tenant, _.copy(limited = 1)).as(
                Outcome.Limited(Bucket.retryAfterSeconds(bucket, settings.ratePerSecond))
              )
            case (_, true) =>
              count(tenant, _.copy(admitted = 1)) >>
                slot(tenant).flatMap(s => s.permit.use(_ => global.permit.use(_ => work))).map(Outcome.Done(_))
          }
      }

  def timedOut(tenant: String): IO[Unit] = count(tenant, _.copy(timedOut = 1))

  def snapshot: IO[Map[String, Counts]] = counts.get

  private def count(tenant: String, delta: Counts => Counts): IO[Unit] =
    val d = delta(Counts.zero)
    counts.update { m =>
      val c = m.getOrElse(tenant, Counts.zero)
      m.updated(tenant, Counts(c.admitted + d.admitted, c.limited + d.limited, c.timedOut + d.timedOut))
    }

  private def slot(tenant: String): IO[Semaphore[IO]] =
    slots.get.map(_.get(tenant)).flatMap {
      case Some(s) => IO.pure(s)
      case None =>
        Semaphore[IO](settings.tenantCap.toLong).flatMap { fresh =>
          slots.modify { m =>
            m.get(tenant) match
              case Some(existing) => (m, existing)
              case None           => (m.updated(tenant, fresh), fresh)
          }
        }
    }

object Gate:
  def apply(settings: AdmissionSettings): IO[Gate] =
    for
      global <- Semaphore[IO](settings.globalConcurrency.toLong)
      slots <- Ref.of[IO, Map[String, Semaphore[IO]]](Map.empty)
      buckets <- Ref.of[IO, Map[String, Bucket]](Map.empty)
      counts <- Ref.of[IO, Map[String, Counts]](Map.empty)
    yield new Gate(settings, global, slots, buckets, counts)
