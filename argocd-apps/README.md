# ArgoCD Applications

이 디렉토리는 ArgoCD Application 리소스들을 관리합니다.

## 디렉토리 구조

```
argocd-apps/
├── frontend-dev.yaml           # 프론트엔드 개발 환경
├── frontend-prod.yaml          # 프론트엔드 운영 환경
├── auth-server-dev.yaml        # 인증 서버 개발 환경
├── auth-server-prod.yaml       # 인증 서버 운영 환경
├── room-server-dev.yaml        # 방 서버 개발 환경
├── room-server-prod.yaml       # 방 서버 운영 환경
├── ticketing-server-dev.yaml   # 티켓팅 서버 개발 환경
├── ticketing-server-prod.yaml  # 티켓팅 서버 운영 환경
├── bot-server-dev.yaml         # 봇 서버 개발 환경
└── captcha-server-dev.yaml     # CAPTCHA 서버 개발 환경
```

## 배포 방법

### 1. 모든 Application 배포

```bash
kubectl apply -f argocd-apps/
```

### 2. 특정 환경만 배포 (개발 환경)

```bash
kubectl apply -f argocd-apps/*-dev.yaml
```

### 3. 특정 서비스만 배포

```bash
kubectl apply -f argocd-apps/room-server-dev.yaml
```

## Application 상태 확인

```bash
# ArgoCD CLI 사용
argocd app list
argocd app get frontend-dev

# kubectl 사용
kubectl get applications -n argocd
kubectl get application frontend-dev -n argocd -o yaml
```

## 브랜치 전략

- **dev 브랜치**: 개발 환경 (dev 네임스페이스)
- **master 브랜치**: 운영 환경 (prod 네임스페이스)

## 자동 동기화 설정

모든 Application은 다음 정책으로 설정되어 있습니다:

- **automated sync**: Git 변경 시 자동 배포
- **selfHeal**: 클러스터 수동 변경 시 Git 상태로 복구
- **prune**: Git에서 삭제된 리소스 자동 삭제

## 새로운 서비스 추가 방법

1. 기존 Application YAML을 복사
2. 서비스 이름과 경로 수정
3. `kubectl apply` 명령으로 배포

예시:
```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: new-service-dev
  namespace: argocd
spec:
  source:
    path: apps/new-service/overlays/dev
  destination:
    namespace: dev
```
