package tfs

import cats.effect.{IO, IOApp, Ref}
import com.comcast.ip4s.*
import org.http4s.Uri
import org.http4s.implicits.*
import org.http4s.ember.client.EmberClientBuilder
import org.http4s.ember.server.EmberServerBuilder
import org.http4s.server.middleware.ErrorHandling
import tfs.config.Platform
import tfs.es.Es
import tfs.http.{Routes, SearchService}
import tfs.tenancy.Gate
import tfs.text.{Models, Tokenizer}
import tfs.understand.{Facets, Parser}

import java.nio.file.Paths

object Main extends IOApp.Simple:
  def run: IO[Unit] =
    Platform.load.flatMap { platform =>
      EmberClientBuilder
        .default[IO]
        .withMaxTotal(512)
        .withMaxPerKey(_ => 256)
        .build
        .use { client =>
          for
            base <- IO.fromEither(Uri.fromString(platform.service.esUrl))
            es = Es(client, base, platform.service.index)
            mapping <- Platform.indexMapping
            _ <- es.ensureIndex(mapping)
            models <- Models(Paths.get(platform.service.modelDir))
            facets <- Ref.of[IO, Map[String, Facets]](Map.empty)
            tokenizer = Tokenizer(platform.text)
            service = SearchService(platform, es, models, tokenizer, Parser(platform.understanding, tokenizer), facets)
            gate <- Gate(platform.admission)
            app = ErrorHandling.httpApp(Routes(platform, service, gate).routes.orNotFound)
            port = Port.fromInt(platform.service.port).getOrElse(port"8080")
            _ <- IO.println(s"tenant-fair-search on :$port, cluster ${platform.service.esUrl}, eval overrides ${platform.service.evalOverrides}")
            _ <- EmberServerBuilder
              .default[IO]
              .withHost(ipv4"0.0.0.0")
              .withPort(port)
              .withHttpApp(app)
              .withMaxConnections(4096)
              .build
              .useForever
          yield ()
        }
    }
