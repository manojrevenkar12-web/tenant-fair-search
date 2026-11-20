package tfs.http

import cats.effect.IO
import io.circe.Json
import io.circe.syntax.*
import org.http4s.{Header, HttpRoutes, Request, Response, Status}
import org.http4s.circe.CirceEntityCodec.*
import org.http4s.dsl.io.*
import org.typelevel.ci.CIString
import tfs.config.Platform
import tfs.tenancy.{Gate, Outcome}

import java.util.concurrent.TimeoutException
import scala.concurrent.duration.*

/** The HTTP surface. The tenant comes from the path and is checked against the configured pattern before anything
  * else; designs and admission modes can be chosen per request only when the evaluation switch is on.
  */
final class Routes(platform: Platform, service: SearchService, gate: Gate):
  private val tenantOk = platform.service.tenantPattern.r
  private val timeout = platform.service.requestTimeoutMs.millis

  private def header(req: Request[IO], name: String): Option[String] =
    if platform.service.evalOverrides then req.headers.get(CIString(name)).map(_.head.value) else None

  private def problem(status: Status, message: String): IO[Response[IO]] =
    IO.pure(Response[IO](status).withEntity(Json.obj("error" -> message.asJson)))

  private def withTenant(tenant: String)(f: => IO[Response[IO]]): IO[Response[IO]] =
    if tenantOk.matches(tenant) then f else problem(Status.BadRequest, "tenant must match " + platform.service.tenantPattern)

  val routes: HttpRoutes[IO] = HttpRoutes.of[IO] {
    case GET -> Root / "health" => Ok(Json.obj("status" -> "ok".asJson))

    case GET -> Root / "v1" / "designs" =>
      Ok(Json.obj("default" -> platform.retrieval.defaultDesign.asJson, "designs" -> platform.designs.keys.toList.sorted.asJson))

    case GET -> Root / "v1" / "metrics" => gate.snapshot.flatMap(m => Ok(m.asJson))

    case req @ POST -> Root / "v1" / "tenants" / tenant / "products" =>
      withTenant(tenant) {
        req.as[List[Product]].flatMap { products =>
          if products.size > platform.service.maxBulk then
            problem(Status.PayloadTooLarge, s"at most ${platform.service.maxBulk} products per request")
          else service.index(tenant, products).flatMap(n => Ok(Json.obj("indexed" -> n.asJson)))
        }
      }

    case DELETE -> Root / "v1" / "tenants" / tenant / "products" =>
      withTenant(tenant)(service.clear(tenant) >> NoContent())

    case req @ POST -> Root / "v1" / "tenants" / tenant / "search" =>
      withTenant(tenant) {
        val designName = header(req, "X-Design").getOrElse(platform.retrieval.defaultDesign)
        val mode = header(req, "X-Admission").getOrElse(platform.admission.mode)
        if service.design(designName).isEmpty then problem(Status.BadRequest, s"unknown design $designName")
        else
          req.as[SearchRequest].flatMap { body =>
            gate
              .run(tenant, mode)(service.search(tenant, designName, body))
              .timeout(timeout)
              .flatMap {
                case Outcome.Done(result) => Ok(result.asJson)
                case Outcome.Limited(seconds) =>
                  problem(Status.TooManyRequests, "rate limit for this tenant").map(
                    _.putHeaders(Header.Raw(CIString("Retry-After"), seconds.toString))
                  )
              }
              .handleErrorWith {
                case _: TimeoutException =>
                  gate.timedOut(tenant) >> problem(Status.ServiceUnavailable, "search timed out")
                case other => IO.raiseError(other)
              }
          }
      }
  }
