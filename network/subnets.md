# Subnet Allocation and Network Access Control (NACL) Analysis

## 1. Subnet Allocation for Block `10.20.0.0/16`

### Requirements
- Address block: `10.20.0.0/16`
- Total available addresses: $2^{16} = 65,536$
- Allocation strategy: Allocate contiguous subnets from largest host requirement to smallest, starting at `10.20.0.0`, using the smallest prefix that satisfies each requirement ($2^{32-\text{prefix}} - 2 \ge \text{required hosts}$).

---

### Step-by-Step Derivation and Working

#### 1. `app` Subnet (1,000 Hosts Needed)
- Usable hosts formula: $2^{32-\text{prefix}} - 2 \ge 1,000$.
- Powers of 2:
  - $2^9 - 2 = 510 < 1,000$ (insufficient)
  - $2^{10} - 2 = 1,022 \ge 1,000$ (sufficient)
- Host bits required: $h = 10$
- Prefix length: $32 - 10 = \mathbf{22}$ (mask: `255.255.252.0`)
- Total addresses in block: $2^{10} = 1,024$ ($4 \times 256$ addresses)
- Network start address: `10.20.0.0`
- IP address span: `10.20.0.0` through `10.20.3.255`
- Usable host range: `10.20.0.1` – `10.20.3.254`
- Broadcast address: `10.20.3.255`
- Usable hosts: $1,022$

#### 2. `public` Subnet (250 Hosts Needed)
- Next contiguous starting address: `10.20.4.0`
- Usable hosts formula: $2^{32-\text{prefix}} - 2 \ge 250$.
- Powers of 2:
  - $2^7 - 2 = 126 < 250$ (insufficient)
  - $2^8 - 2 = 254 \ge 250$ (sufficient)
- Host bits required: $h = 8$
- Prefix length: $32 - 8 = \mathbf{24}$ (mask: `255.255.255.0`)
- Total addresses in block: $2^8 = 256$ addresses
- Network start address: `10.20.4.0`
- IP address span: `10.20.4.0` through `10.20.4.255`
- Usable host range: `10.20.4.1` – `10.20.4.254`
- Broadcast address: `10.20.4.255`
- Usable hosts: $254$

#### 3. `data` Subnet (100 Hosts Needed)
- Next contiguous starting address: `10.20.5.0`
- Usable hosts formula: $2^{32-\text{prefix}} - 2 \ge 100$.
- Powers of 2:
  - $2^6 - 2 = 62 < 100$ (insufficient)
  - $2^7 - 2 = 126 \ge 100$ (sufficient)
- Host bits required: $h = 7$
- Prefix length: $32 - 7 = \mathbf{25}$ (mask: `255.255.255.128`)
- Total addresses in block: $2^7 = 128$ addresses
- Network start address: `10.20.5.0`
- IP address span: `10.20.5.0` through `10.20.5.127`
- Usable host range: `10.20.5.1` – `10.20.5.126`
- Broadcast address: `10.20.5.127`
- Usable hosts: $126$

#### 4. `management` Subnet (20 Hosts Needed)
- Next contiguous starting address: `10.20.5.128`
- Usable hosts formula: $2^{32-\text{prefix}} - 2 \ge 20$.
- Powers of 2:
  - $2^4 - 2 = 14 < 20$ (insufficient)
  - $2^5 - 2 = 30 \ge 20$ (sufficient)
- Host bits required: $h = 5$
- Prefix length: $32 - 5 = \mathbf{27}$ (mask: `255.255.255.224`)
- Total addresses in block: $2^5 = 32$ addresses
- Network start address: `10.20.5.128`
- IP address span: `10.20.5.128` through `10.20.5.159`
- Usable host range: `10.20.5.129` – `10.20.5.158`
- Broadcast address: `10.20.5.159`
- Usable hosts: $30$

---

### Subnet Allocation Table

| Subnet Name | Network Address | Prefix Length | Usable Host Range | Broadcast Address | Number of Usable Hosts |
| :--- | :--- | :---: | :--- | :--- | :---: |
| **app** | `10.20.0.0` | `/22` | `10.20.0.1` – `10.20.3.254` | `10.20.3.255` | 1,022 |
| **public** | `10.20.4.0` | `/24` | `10.20.4.1` – `10.20.4.254` | `10.20.4.255` | 254 |
| **data** | `10.20.5.0` | `/25` | `10.20.5.1` – `10.20.5.126` | `10.20.5.127` | 126 |
| **management** | `10.20.5.128` | `/27` | `10.20.5.129` – `10.20.5.158` | `10.20.5.159` | 30 |

---

## 2. Stateless NACL Reasoning & Explanation

### Why a Stateless NACL Requires Separate Rules for Reply Traffic
Unlike stateful firewalls (such as AWS Security Groups or iptables with conntrack), a Network Access Control List (NACL) is strictly **stateless**. It does not maintain an internal connection state table tracking existing TCP sessions, three-way handshakes, or ephemeral return paths.

Consequently, every packet is inspected independently against the rule list based solely on its individual headers (source IP, destination IP, protocol, source port, and destination port):
1. **Outbound Responses to External Clients**: When an external client sends an HTTP (TCP 80) or HTTPS (TCP 443) request from an ephemeral port (typically in the range 1024–65535) to the public load balancer, the inbound traffic matches the ingress allow rule. However, when the load balancer transmits the response packet back to the client, the outbound packet has source port 80/443 and destination port set to the client's ephemeral port. Without an explicit outbound allow rule covering TCP destination ports 1024–65535 to `0.0.0.0/0`, the response packet hits the implicit default DENY and is dropped.
2. **Inbound Replies from Internal Backend (App Subnet)**: When the load balancer proxies traffic by opening a TCP connection to backend pods in the `app` subnet on destination port 8000, the outbound packet matches the outbound rule. However, the returning backend response packet arrives at the public subnet's inbound interface with source IP in `10.20.0.0/22`, source port 8000, and destination port in the load balancer's ephemeral port range (1024–65535). Because the NACL has no concept of established sessions, this return traffic will be dropped unless an explicit inbound rule permits TCP ephemeral ports 1024–65535 originating from `10.20.0.0/22`.

### Why Rule Order Matters for the `198.51.100.0/24` Block
NACL evaluation follows a strict top-down, first-match termination model:
- Rules are evaluated sequentially starting from the lowest rule number.
- As soon as a packet matches a rule's filter criteria (CIDR, protocol, and port range), the associated action (`allow` or `deny`) is applied immediately, and evaluation ceases.
- If no rules match, the packet is denied by default.

The requirement dictates blocking **all** traffic from the abusive range `198.51.100.0/24`, including traffic targeting standard web ports (TCP 80 and TCP 443).
- Because web traffic rules allow connections from anywhere (`0.0.0.0/0`), the CIDR `198.51.100.0/24` is a subset of `0.0.0.0/0`.
- If the allow rules (e.g., allow TCP 80/443 from `0.0.0.0/0`) were assigned lower rule numbers (e.g., Rule 100) and the deny rule for `198.51.100.0/24` had a higher rule number (e.g., Rule 200), an inbound web packet from `198.51.100.9` on port 443 would match Rule 100 first and be permitted. The deny rule would never be evaluated for web traffic.
- Therefore, the explicit DENY rule for `198.51.100.0/24` must be placed at a strictly **lower rule number** (e.g., Rule 100) than the general ALLOW rules for `0.0.0.0/0` (Rules 200 and 210). This guarantees that any packet originating from `198.51.100.0/24` is blocked instantly, regardless of destination port.

