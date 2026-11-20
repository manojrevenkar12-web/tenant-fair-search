ThisBuild / scalaVersion := "3.3.4"
ThisBuild / organization := "dev.manojrevenkar12"

val http4sVersion = "0.23.30"
val circeVersion = "0.14.10"

lazy val service = (project in file("service"))
  .settings(
    name := "tenant-fair-search",
    libraryDependencies ++= Seq(
      "org.typelevel" %% "cats-effect" % "3.5.7",
      "org.http4s" %% "http4s-ember-server" % http4sVersion,
      "org.http4s" %% "http4s-ember-client" % http4sVersion,
      "org.http4s" %% "http4s-dsl" % http4sVersion,
      "org.http4s" %% "http4s-circe" % http4sVersion,
      "io.circe" %% "circe-core" % circeVersion,
      "io.circe" %% "circe-generic" % circeVersion,
      "io.circe" %% "circe-parser" % circeVersion,
      "org.slf4j" % "slf4j-nop" % "2.0.16",
      "org.scalameta" %% "munit" % "1.0.3" % Test,
      "org.typelevel" %% "munit-cats-effect" % "2.0.0" % Test
    ),
    scalacOptions ++= Seq("-deprecation", "-feature", "-unchecked", "-Wunused:imports"),
    assembly / mainClass := Some("tfs.Main"),
    assembly / assemblyJarName := "tenant-fair-search.jar",
    assembly / assemblyMergeStrategy := {
      case PathList("META-INF", "versions", _, "module-info.class") => MergeStrategy.discard
      case "module-info.class"                                      => MergeStrategy.discard
      case x =>
        val previous = (assembly / assemblyMergeStrategy).value
        previous(x)
    }
  )

lazy val root = (project in file(".")).aggregate(service).settings(publish / skip := true)
