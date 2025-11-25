# Monitoring Stack (kube-prometheus-stack)

Kubernetes 클러스터 모니터링을 위한 표준 스택입니다.

## 구성 요소

- **Prometheus Operator**: Prometheus 인스턴스 자동 관리
- **Prometheus**: 메트릭 수집 및 저장
- **Grafana**: 시각화 대시보드 (30+ 기본 대시보드 포함)
- **Alertmanager**: 알림 관리
- **Node Exporter**: 노드 메트릭 수집 (DaemonSet)
- **Kube State Metrics**: Kubernetes 리소스 메트릭

## 설치 방법

### 1. 기존 커스텀 모니터링 스택 제거

```bash
cd ~/tickget-k8s-manifest

# Prometheus, Grafana, Node Exporter, Kube State Metrics만 제거
kubectl delete statefulset prometheus -n monitoring
kubectl delete deployment grafana kube-state-metrics -n monitoring
kubectl delete daemonset node-exporter -n monitoring
kubectl delete svc prometheus prometheus-headless grafana kube-state-metrics node-exporter -n monitoring

# ConfigMap, Secret 정리
kubectl delete configmap prometheus-config -n monitoring 2>/dev/null || true
kubectl delete configmap grafana-config -n monitoring 2>/dev/null || true
kubectl delete secret grafana-secret -n monitoring 2>/dev/null || true

# PVC 제거 (데이터 삭제됨, 주의!)
kubectl delete pvc prometheus-storage-prometheus-0 grafana-pvc -n monitoring
```

### 2. Helm Repository 추가

```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update
```

### 3. kube-prometheus-stack 설치

```bash
helm install kube-prometheus-stack prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --values infra/monitoring/kube-prometheus-stack-values.yaml
```

### 4. Grafana IngressRoute 업데이트

서비스 이름이 변경되었으므로 업데이트:

```bash
# grafana-ingress.yaml 수정 (서비스 이름: grafana → kube-prometheus-stack-grafana)
kubectl apply -f infra/monitoring/grafana-ingress.yaml
```

### 5. 설치 확인

```bash
# Pod 상태 확인
kubectl get pods -n monitoring

# 서비스 확인
kubectl get svc -n monitoring | grep kube-prometheus

# Grafana 접속
# https://grafana.tickget.kr
# 초기 로그인: admin / tickget209
```

## 업그레이드

```bash
helm upgrade kube-prometheus-stack prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --values infra/monitoring/kube-prometheus-stack-values.yaml
```

## 제거

```bash
helm uninstall kube-prometheus-stack -n monitoring
```

## 주요 대시보드

설치 후 Grafana에서 자동으로 제공되는 대시보드:

1. **Kubernetes / Compute Resources / Cluster**: 클러스터 전체 리소스 사용량
2. **Kubernetes / Compute Resources / Namespace (Pods)**: 네임스페이스별 Pod 리소스
3. **Kubernetes / Compute Resources / Node (Pods)**: 노드별 Pod 리소스
4. **Kubernetes / Networking / Cluster**: 클러스터 네트워크 메트릭
5. **Node Exporter / Nodes**: 노드 상세 메트릭 (CPU, Memory, Disk, Network)
6. **Prometheus / Overview**: Prometheus 자체 메트릭

## 커스텀 메트릭 수집

애플리케이션 메트릭을 수집하려면 ServiceMonitor를 생성:

```yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: my-app
  namespace: monitoring
spec:
  selector:
    matchLabels:
      app: my-app
  endpoints:
    - port: metrics
      interval: 30s
```

## 알림 설정

Alertmanager 설정은 `kube-prometheus-stack-values.yaml`에서 수정:

```yaml
alertmanager:
  config:
    route:
      receiver: 'default'
    receivers:
      - name: 'default'
        # Slack, Email 등 알림 채널 설정
```

## 트러블슈팅

### Grafana 로그인 비밀번호 분실

```bash
kubectl get secret -n monitoring kube-prometheus-stack-grafana -o jsonpath="{.data.admin-password}" | base64 --decode
```

### Prometheus 데이터 용량 부족

values.yaml에서 스토리지 크기 증가 후 재설치

### ServiceMonitor가 메트릭을 수집하지 못함

```bash
# Prometheus targets 확인
kubectl port-forward -n monitoring svc/kube-prometheus-stack-prometheus 9090:9090
# http://localhost:9090/targets 접속
```

## 참고 자료

- [kube-prometheus-stack 공식 문서](https://github.com/prometheus-community/helm-charts/tree/main/charts/kube-prometheus-stack)
- [Prometheus Operator 문서](https://prometheus-operator.dev/)
- [Grafana 대시보드 갤러리](https://grafana.com/grafana/dashboards/)
