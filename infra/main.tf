terraform {
  required_providers {
    docker = {
      source  = "kreuzwerker/docker"
      version = "~> 3.0"
    }
  }
}
provider "docker" {}

resource "docker_image" "app" {
  name = var.image_name
}

resource "docker_container" "app" {
  name     = "ci-lab-deploy"
  image    = docker_image.app.image_id
  command  = ["pytest", "-v"]
  rm       = false
  must_run = false
}

output "container_id" {
  value       = docker_container.app.id
  description = "Ідентифікатор запущеного контейнера"
}
