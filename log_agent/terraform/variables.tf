variable "aws_region" {
  default = "us-west-2"
}

variable "instance_type" {
  description = "EC2 instance type to use for the VM"
  # 4 vCPU, 8 GiB RAM
  default     = "c5.xlarge"
}

variable "key_name" {
  default = "terraform-ec2-key"
}

variable "public_key_path" {
  default = "./aws-ec2-key.pub"
}

variable "root_volume_size" {
  description = "Root EBS volume size in GB"
  type        = number
  default     = 50
}