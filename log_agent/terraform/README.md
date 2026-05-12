# Terraform — EC2 VM provisioning guide

This document covers provisioning the demo EC2 instance using the Terraform configuration in this directory, connecting to it over SSH, and getting the Docker stack running on it.

---

## Prerequisites

Before running Terraform, you need:

- **Terraform v1.x** on your PATH. Verify with `terraform version`.
- **AWS CLI** configured with credentials that have permissions to create: VPC resources (subnets, internet gateway, route tables), EC2 key pairs, security groups, and EC2 instances. The simplest approach for a personal demo is a credentials profile with `ec2:*` and `vpc:*` permissions.
- **An SSH key pair.** Terraform registers the public key with AWS as an EC2 key pair. The private key stays local and is used to connect. If you do not have one, generate it:

  ```bash
  ssh-keygen -t ed25519 -f ~/.ssh/aws-ec2-key -C "log-intel-demo"
  ```

  On Windows, the default output path is `C:\Users\<you>\.ssh\aws-ec2-key` and `aws-ec2-key.pub`.

---

## What the Terraform configuration provisions

`main.tf` creates the following resources in the target AWS region:

- A VPC with a public subnet, internet gateway, and route table.
- An EC2 key pair registered from your supplied public key.
- A security group with inbound rules for SSH (22), the FastAPI service (8000), the web UI (8080), Kibana (5601), and Elasticsearch (9200). Review and tighten these rules before exposing to the internet.
- An `aws_instance` resource (Ubuntu) with a configurable instance type and a 50 GB root EBS volume by default.

`variables.tf` exposes the following inputs:

| Variable           | Default             | Notes                            |
| ------------------ | ------------------- | -------------------------------- |
| `aws_region`       | `us-west-2`         | Target region                    |
| `instance_type`    | `t3.xlarge`         | 4 vCPU / 16 GiB. See note below. |
| `key_name`         | `terraform-ec2-key` | Name registered in EC2           |
| `public_key_path`  | `./aws-ec2-key.pub` | Path to your public key file     |
| `root_volume_size` | `50`                | Root EBS volume in GB            |

**Instance sizing note:** `t3.xlarge` (4 vCPU, 16 GiB) is the recommended minimum for running Kafka, Elasticsearch, and the Python services concurrently without constant OOM pressure. `c5.xlarge` (4 vCPU, 8 GiB) will work if you reduce the Elasticsearch heap to 1–2 GB. `t3.medium` (2 vCPU, 4 GiB) is tight and not recommended unless you are only testing one service at a time.

---

## Provisioning the VM

### 1. Place your public key

Copy your public key into the `terraform/` directory or note its absolute path. The path passed via `-var "public_key_path=..."` must point to a readable `.pub` file.

On Windows (PowerShell), confirm the file is present:

```powershell
cd "D:\log agent\terraform" #example
Get-ChildItem -Path .\aws-ec2-key.pub
```

### 2. Initialize Terraform

```powershell
terraform init
```

This downloads the AWS provider and sets up the local state backend.

### 3. Plan and apply

Review what Terraform will create before applying:

```powershell
terraform plan `
  -var "instance_type=t3.xlarge" `
  -var "root_volume_size=50" `
  -var "public_key_path=./aws-ec2-key.pub"
```

Apply (creates the resources):

```powershell
terraform apply -auto-approve `
  -var "instance_type=t3.xlarge" `
  -var "root_volume_size=50" `
  -var "public_key_path=./aws-ec2-key.pub"
```

To use `c5.xlarge` instead:

```powershell
terraform apply -auto-approve `
  -var "instance_type=c5.xlarge" `
  -var "root_volume_size=50" `
  -var "public_key_path=./aws-ec2-key.pub"
```

Apply typically completes in 60–90 seconds. The instance needs another 30–60 seconds to finish its initial boot before SSH is available.

---

## Getting the VM public IP

The current Terraform configuration does not declare an output for the public IP. Retrieve it one of two ways:

**AWS Console:** EC2 → Instances → filter by tag `Name: Terraform-EC2` → Public IPv4 address.

**AWS CLI:**

```bash
aws ec2 describe-instances \
  --filters "Name=tag:Name,Values=Terraform-EC2" \
  --query 'Reservations[].Instances[].PublicIpAddress' \
  --output text
```

To have Terraform print the IP on every apply, add this block to `main.tf`:

```hcl
output "instance_public_ip" {
  value = aws_instance.vm.public_ip
}
```

---

## Connecting via SSH

```bash
# Linux / macOS
ssh -i ~/.ssh/aws-ec2-key ubuntu@<VM_PUBLIC_IP>
```

```powershell
# Windows PowerShell
ssh -i "$env:USERPROFILE\.ssh\aws-ec2-key" ubuntu@<VM_PUBLIC_IP>
```

### Fixing SSH key permissions on Windows

OpenSSH on Windows rejects private key files that are readable by other users. If SSH reports a permissions warning and refuses to use the key, fix the ACLs:

```powershell
# Run from the directory containing the private key.
# Elevate PowerShell if takeown fails.
takeown /f .\aws-ec2-key
icacls .\aws-ec2-key /inheritance:r
icacls .\aws-ec2-key /grant:r "%USERDOMAIN%\%USERNAME%:R"
```

After this, retry the SSH connection.

---

## Installing Docker on the VM

The EC2 instance does not have Docker pre-installed. Run the following on the VM after SSH-ing in:

```bash
sudo apt-get update
sudo apt-get install -y ca-certificates curl gnupg lsb-release

sudo mkdir -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
  | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
  https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" \
  | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

sudo systemctl enable --now docker

# Allow the ubuntu user to run docker without sudo
sudo usermod -aG docker $USER
newgrp docker
```

Verify the installation:

```bash
docker version
docker compose version
```

---

## Copying the project to the VM

**Option A — Git clone (recommended)**

Push the repository to a remote (GitHub, GitLab, or similar) and clone it on the VM:

```bash
git clone https://github.com/<your-org>/log-intel-rca-demo.git ~/log-intel-rca-demo
```

This makes future updates straightforward: `git pull` on the VM rather than re-copying files.

**Option B — SCP**

Transfer the project directory from your workstation:

```powershell
# Windows PowerShell — run from the directory containing log-intel-rca-demo
scp -i "$env:USERPROFILE\.ssh\aws-ec2-key" -r "D:\log agent\log-intel-rca-demo" ubuntu@<VM_PUBLIC_IP>:/home/ubuntu/ #example D drive path
```

Make sure you copy the entire `log-intel-rca-demo/` directory, including `services/`. The Docker build contexts reference paths inside `services/` and will fail if that directory is absent.

---

## Starting the demo stack

```bash
cd ~/log-intel-rca-demo

# Pull pre-built images and build local service images
docker compose pull
docker compose up -d --build

# Check container status
docker compose ps
```

Allow 60–90 seconds for Elasticsearch and Kafka to initialize. Once all containers show `Up`, verify the API:

```bash
curl -I http://127.0.0.1:8000/docs
```

Then access from your workstation:

| Service       | URL                               |
| ------------- | --------------------------------- |
| Web UI        | `http://<VM_PUBLIC_IP>:8080`      |
| FastAPI docs  | `http://<VM_PUBLIC_IP>:8000/docs` |
| Kibana        | `http://<VM_PUBLIC_IP>:5601`      |
| Elasticsearch | `http://<VM_PUBLIC_IP>:9200`      |

---

## Troubleshooting

### Containers unreachable from outside the VM

The EC2 security group controls what reaches the instance from the internet. The most common cause of "works on localhost, fails from my browser" is a missing inbound rule.

Check the security group in the AWS console or via CLI, and confirm rules exist for TCP 8000 and 8080 from your IP (or `0.0.0.0/0` for a demo). Also check whether UFW is active on the VM:

```bash
sudo ufw status
```

If UFW is enabled, allow the ports:

```bash
sudo ufw allow 8000/tcp
sudo ufw allow 8080/tcp
```

### Elasticsearch exits on startup

The two most common causes:

**`vm.max_map_count` too low** — Elasticsearch requires at least 262144. Set it:

```bash
sudo sysctl -w vm.max_map_count=262144
echo 'vm.max_map_count=262144' | sudo tee -a /etc/sysctl.conf
```

**JVM heap exceeds available memory** — If the instance has 8 GiB or less, reduce the heap in `docker-compose.yml`:

```yaml
environment:
  - ES_JAVA_OPTS=-Xms1g -Xmx1g
```

Then restart:

```bash
docker compose down
docker compose up -d --build
```

### Kafka or consumer keeps restarting

Check logs:

```bash
docker compose logs kafka --tail 200
docker compose logs kafka-consumer --tail 200
```

Kafka takes 15–30 seconds to become ready. The consumer exits if it cannot connect during its startup window and Docker restarts it. This usually resolves itself within a few restart cycles. If it does not stabilize, look for port conflicts or memory pressure.

### Build error: "unable to prepare context: path not found"

Docker cannot find the build context for a service. This means the `services/<name>` directory was not copied to the VM. Copy the full project directory as described above.

### General log inspection

```bash
# All containers
docker compose ps --all

# Logs for a specific service
docker compose logs <service-name> --tail 200

# Follow logs in real time
docker compose logs -f <service-name>
```

---

## Tearing down

To destroy all AWS resources created by this configuration:

```powershell
cd "D:\log agent\terraform" #example D Drive path
terraform destroy -auto-approve -var "public_key_path=./aws-ec2-key.pub"
```

This removes the EC2 instance, security group, subnet, route table, internet gateway, VPC, and key pair. It does not delete any data you stored outside of these resources (e.g., S3 buckets, if any).
