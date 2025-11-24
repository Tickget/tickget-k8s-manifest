# Cert-Manager 설치 가이드

## 개요

Cert-Manager는 Kubernetes에서 TLS 인증서를 자동으로 발급, 갱신, 관리하는 도구입니다.
Let's Encrypt와 연동하여 무료 TLS 인증서를 자동으로 발급받을 수 있습니다.

## 설치 방법

### 1. Cert-Manager 설치

공식 매니페스트를 사용하여 설치합니다 (v1.16.3 - 최신 안정 버전):

```bash
# cert-manager 네임스페이스에 설치
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.16.3/cert-manager.yaml
```

### 2. 설치 확인

```bash
# Pod 상태 확인 (모두 Running이 될 때까지 대기)
kubectl get pods -n cert-manager

# 예상 결과:
# NAME                                       READY   STATUS    RESTARTS   AGE
# cert-manager-xxxxxxxxxx-xxxxx              1/1     Running   0          1m
# cert-manager-cainjector-xxxxxxxxxx-xxxxx   1/1     Running   0          1m
# cert-manager-webhook-xxxxxxxxxx-xxxxx      1/1     Running   0          1m
```

### 3. CRD 확인

```bash
# Cert-Manager CRD 확인
kubectl get crd | grep cert-manager

# 예상 결과:
# certificaterequests.cert-manager.io
# certificates.cert-manager.io
# challenges.acme.cert-manager.io
# clusterissuers.cert-manager.io
# issuers.cert-manager.io
# orders.acme.cert-manager.io
```

### 4. ClusterIssuer 적용

Let's Encrypt ClusterIssuer를 적용합니다 (이미 `common/cluster-issuer.yaml`에 정의되어 있음):

```bash
# ClusterIssuer 적용
cd ~/tickget-k8s-manifest
kubectl apply -f common/cluster-issuer.yaml

# ClusterIssuer 확인
kubectl get clusterissuer

# 상세 정보 확인
kubectl describe clusterissuer letsencrypt-prod
kubectl describe clusterissuer letsencrypt-staging
```

## ClusterIssuer 설정

### Staging (테스트용)

- **이름**: `letsencrypt-staging`
- **용도**: 테스트 및 개발 환경
- **Rate Limit**: 높음 (시간당 많은 요청 가능)
- **인증서**: 신뢰할 수 없는 인증서 (브라우저 경고 표시)

### Production (프로덕션용)

- **이름**: `letsencrypt-prod`
- **용도**: 프로덕션 환경
- **Rate Limit**: 낮음 (주당 50개 인증서)
- **인증서**: 신뢰할 수 있는 인증서 (브라우저에서 정상 표시)

## Ingress에서 TLS 인증서 자동 발급

Traefik IngressRoute에서 Cert-Manager를 사용하려면 다음과 같이 설정합니다:

```yaml
apiVersion: traefik.io/v1alpha1
kind: IngressRoute
metadata:
  name: example-ingress
  namespace: dev
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod  # Production 인증서
spec:
  entryPoints:
    - websecure
  routes:
    - match: Host(`example.tickget.kr`)
      kind: Rule
      services:
        - name: example-service
          port: 80
  tls:
    secretName: example-tls  # 인증서가 저장될 Secret 이름
```

Cert-Manager가 자동으로:
1. Let's Encrypt에 인증서 발급 요청
2. HTTP-01 Challenge 수행 (Traefik이 자동으로 처리)
3. 인증서 발급 완료 후 `example-tls` Secret에 저장
4. 인증서 만료 30일 전 자동 갱신

## 인증서 확인

```bash
# Certificate 리소스 확인
kubectl get certificate -A

# 특정 Certificate 상세 정보
kubectl describe certificate <certificate-name> -n <namespace>

# TLS Secret 확인
kubectl get secret <secret-name> -n <namespace> -o yaml
```

## 트러블슈팅

### Pod가 Running 상태가 안 됨

```bash
# Pod 로그 확인
kubectl logs -n cert-manager -l app=cert-manager
kubectl logs -n cert-manager -l app=webhook
kubectl logs -n cert-manager -l app=cainjector
```

### 인증서 발급 실패

```bash
# Certificate 상태 확인
kubectl describe certificate <certificate-name> -n <namespace>

# CertificateRequest 확인
kubectl get certificaterequest -n <namespace>
kubectl describe certificaterequest <request-name> -n <namespace>

# Challenge 확인 (HTTP-01)
kubectl get challenge -A
kubectl describe challenge <challenge-name> -n <namespace>
```

### Let's Encrypt Rate Limit 초과

- Staging을 먼저 사용하여 테스트
- Production은 정상 작동 확인 후 사용
- Rate Limit: https://letsencrypt.org/docs/rate-limits/

## 참고 자료

- 공식 문서: https://cert-manager.io/docs/
- 설치 가이드: https://cert-manager.io/docs/installation/
- Traefik 연동: https://cert-manager.io/docs/usage/ingress/
- Let's Encrypt: https://letsencrypt.org/

## 버전 정보

- Cert-Manager: v1.16.3
- Kubernetes: v1.33.5 (K3s)
- Let's Encrypt: ACME v2
