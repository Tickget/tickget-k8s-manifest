# Elasticsearch + Kibana 배포 가이드

## 아키텍처

```
┌─────────────────────────────────────────────────┐
│  Elasticsearch (default namespace)              │
│  - 공통 인프라 (Redis, Kafka와 동일)            │
│  - dev/test/prod 모든 환경에서 공유              │
│  - 인덱스로 환경 구분                            │
│    - tickget-dev-concert-halls                   │
│    - tickget-prod-concert-halls                  │
└─────────────────────────────────────────────────┘
                    ▲
                    │ http://elasticsearch-service.default:9200
                    │
┌─────────────────────────────────────────────────┐
│  Kibana UI (monitoring namespace)               │
│  - 모니터링 도구 (Grafana와 동일)               │
│  - 도메인: https://es.tickget.kr                 │
└─────────────────────────────────────────────────┘
```

## 리소스 할당

**Elasticsearch (default namespace):**
- CPU: 250m ~ 500m (0.25 ~ 0.5 core)
- Memory: 512Mi ~ 1Gi
- Storage: 10Gi (PersistentVolume)
- JVM Heap: 256m ~ 512m

**Kibana (monitoring namespace):**
- CPU: 100m ~ 250m (0.1 ~ 0.25 core)
- Memory: 256Mi ~ 512Mi

**예상 총 메모리 사용량:** ~1.5GB

## 배포 순서

### 1. TLS Secret 생성

es.tickget.kr 도메인용 TLS 인증서를 생성합니다:

```bash
# monitoring namespace에 TLS secret 생성
# 방법 1: 기존 cert 복사
kubectl get secret tickget-kr-tls -n default -o yaml | \
  sed 's/namespace: default/namespace: monitoring/' | \
  sed 's/name: tickget-kr-tls/name: es-tickget-kr-tls/' | \
  kubectl apply -f -

# 방법 2: cert-manager로 자동 생성 (권장)
cat <<EOF | kubectl apply -f -
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: es-tickget-kr-cert
  namespace: monitoring
spec:
  secretName: es-tickget-kr-tls
  issuerRef:
    name: letsencrypt-prod
    kind: ClusterIssuer
  dnsNames:
    - es.tickget.kr
EOF
```

### 2. Elasticsearch + Kibana 배포

```bash
cd tickget-k8s-manifests/infra/elasticsearch

# 전체 배포 (Elasticsearch + Kibana)
kubectl apply -k .

# 개별 확인
kubectl get all -n default -l app=elasticsearch
kubectl get all -n monitoring -l app=kibana
```

### 3. 배포 상태 확인

```bash
# Elasticsearch 파드 상태
kubectl get pods -n default -l app=elasticsearch -w

# Elasticsearch 로그 확인
kubectl logs -n default -l app=elasticsearch --tail=100 -f

# Kibana 파드 상태
kubectl get pods -n monitoring -l app=kibana -w

# Kibana 로그 확인
kubectl logs -n monitoring -l app=kibana --tail=100 -f
```

### 4. Elasticsearch Health Check

```bash
# Cluster health 확인
kubectl exec -n default elasticsearch-0 -- curl -s http://localhost:9200/_cluster/health?pretty

# 노드 정보 확인
kubectl exec -n default elasticsearch-0 -- curl -s http://localhost:9200/_cat/nodes?v

# 인덱스 목록 확인
kubectl exec -n default elasticsearch-0 -- curl -s http://localhost:9200/_cat/indices?v
```

### 5. Kibana 접속

브라우저에서 접속:
```
https://es.tickget.kr
```

## 애플리케이션에서 사용하기

### Spring Boot (dev namespace)

```yaml
# application-dev.yml
spring:
  elasticsearch:
    uris: http://elasticsearch-service.default.svc.cluster.local:9200
```

### 환경별 인덱스 네이밍

```java
// dev 환경
String indexName = "tickget-dev-concert-halls";

// prod 환경
String indexName = "tickget-prod-concert-halls";
```

## 한글 검색 설정

### 1. Nori 플러그인 설치 (선택사항)

Elasticsearch 파드 내부에서 실행:

```bash
kubectl exec -n default elasticsearch-0 -- \
  bin/elasticsearch-plugin install analysis-nori
```

**재시작 필요:**
```bash
kubectl rollout restart statefulset/elasticsearch -n default
```

### 2. 인덱스 생성 (한글 분석기 적용)

```bash
# 인덱스 생성 스크립트 실행 (별도 제공)
kubectl exec -n default elasticsearch-0 -- curl -X PUT \
  "localhost:9200/tickget-dev-concert-halls" \
  -H 'Content-Type: application/json' \
  -d @/path/to/index-mapping.json
```

## 트러블슈팅

### Elasticsearch가 시작되지 않는 경우

**문제:** `vm.max_map_count` 설정 오류

**해결:**
```bash
# Worker 노드에서 실행
sudo sysctl -w vm.max_map_count=262144

# 영구 적용
echo "vm.max_map_count=262144" | sudo tee -a /etc/sysctl.conf
sudo sysctl -p
```

### Kibana가 Elasticsearch에 연결되지 않는 경우

**확인 사항:**
1. Elasticsearch가 정상 실행 중인지 확인
2. 네임스페이스 간 통신 확인

```bash
# Kibana 파드에서 Elasticsearch 연결 테스트
kubectl exec -n monitoring $(kubectl get pod -n monitoring -l app=kibana -o name) -- \
  curl -s http://elasticsearch-service.default.svc.cluster.local:9200
```

### 메모리 부족 문제

Elasticsearch가 OOMKilled되는 경우:

1. JVM Heap 크기 줄이기 (configmap 수정)
2. 리소스 limit 증가 (statefulset 수정)

```bash
kubectl edit statefulset elasticsearch -n default
```

## 데이터 동기화

MySQL → Elasticsearch 데이터 동기화는 별도 스크립트로 제공됩니다:
- `sync-concert-halls.py` (Python)
- 또는 Spring Batch로 구현

## 백업 및 복원

### 스냅샷 생성

```bash
# 스냅샷 저장소 등록 (S3 사용)
kubectl exec -n default elasticsearch-0 -- curl -X PUT \
  "localhost:9200/_snapshot/s3_backup" \
  -H 'Content-Type: application/json' \
  -d '{"type": "s3", "settings": {"bucket": "tickget-es-backup"}}'

# 스냅샷 생성
kubectl exec -n default elasticsearch-0 -- curl -X PUT \
  "localhost:9200/_snapshot/s3_backup/snapshot_$(date +%Y%m%d)"
```

## 모니터링

### Prometheus Exporter (선택사항)

Elasticsearch metrics를 Prometheus로 수집하려면:

```bash
kubectl apply -f elasticsearch-exporter.yaml
```

### Kibana에서 모니터링

1. https://es.tickget.kr 접속
2. Stack Monitoring 메뉴 이동
3. Elasticsearch 클러스터 상태 확인

## 정리 (삭제)

```bash
# 전체 삭제
kubectl delete -k tickget-k8s-manifests/infra/elasticsearch

# 개별 삭제
kubectl delete statefulset elasticsearch -n default
kubectl delete deployment kibana -n monitoring

# PVC도 함께 삭제 (주의: 데이터 손실)
kubectl delete pvc elasticsearch-data-elasticsearch-0 -n default
```

## 참고 자료

- [Elasticsearch on Kubernetes](https://www.elastic.co/guide/en/cloud-on-k8s/current/index.html)
- [Nori 한글 분석기](https://www.elastic.co/guide/en/elasticsearch/plugins/current/analysis-nori.html)
- [Kibana 가이드](https://www.elastic.co/guide/en/kibana/current/index.html)
