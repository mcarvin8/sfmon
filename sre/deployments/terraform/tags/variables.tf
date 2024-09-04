variable "environment_runtime" {
  type        = string
  description = "Name of runtime environment. Leave empty to omit environment tags."
  default     = ""
}

variable "owner" {
  type        = string
  description = "E-mail address of technical contact"
}

variable "repo" {
  type        = string
  description = "Source control repository that configuration can be found in"
}
