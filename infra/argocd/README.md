# ArgoCD 설치 가이드 (Helm)

## 개요

ArgoCD는 Kubernetes를 위한 선언적 GitOps 지속적 배포 도구입니다.
Git 저장소를 단일 진실 공급원(Single Source of Truth)으로 사용하여 애플리케이션을 배포하고 관리합니다.

**설치 방식:** Helm Chart (공식 권장 방법)

## 사전 요구사항

- Kubernetes 클러스터 (K3s v1.33.5+)
- kubectl 설치 및 구성
- Helm 3.x 설치
- Cert-Manager 설치 완료 (TLS 인증서 자동 발급용)

## 설치 방법

### 1. Helm 설치 (EC2 master 노드)

```bash
# Helm 3 설치 스크립트
curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash

# 설치 확인
helm version

# 예상 결과:
# version.BuildInfo{Version:"v3.x.x", GitCommit:"...", GitTreeState:"clean", GoVersion:"go1.x.x"}
```

### 2. ArgoCD Helm Repository 추가

```bash
# ArgoCD Helm Repository 추가
helm repo add argo https://argoproj.github.io/argo-helm

# Repository 업데이트
helm repo update

# ArgoCD Chart 확인
helm search repo argo/argo-cd
```

### 3. ArgoCD 설치

#### 옵션 A: 기본 설치 (빠른 시작)

```bash
# 기본 설정으로 설치
helm install argocd argo/argo-cd \
  --namespace argocd \
  --create-namespace \
  --version 7.x.x  # 최신 stable 버전 사용

# 설치 확인
kubectl get pods -n argocd --watch
```

#### 옵션 B: 커스텀 설정으로 설치 (권장)

```bash
# values.yaml 파일 사용
helm install argocd argo/argo-cd \
  --namespace argocd \
  --create-namespace \
  --values infra/argocd/values.yaml

# 또는 개별 값 지정
helm install argocd argo/argo-cd \
  --namespace argocd \
  --create-namespace \
  --set server.service.type=ClusterIP \
  --set configs.params."server\.insecure"=true
```

### 4. 설치 확인

```bash
# Pod 상태 확인 (모두 Running이 될 때까지 대기, 1-2분 소요)
kubectl get pods -n argocd

# 서비스 확인
kubectl get svc -n argocd

# Helm Release 확인
helm list -n argocd
```

**예상 결과:**
```bash
$ kubectl get pods -n argocd
NAME                                                READY   STATUS    RESTARTS   AGE
argocd-application-controller-0                     1/1     Running   0          2m
argocd-applicationset-controller-xxxxxxxxx-xxxxx    1/1     Running   0          2m
argocd-dex-server-xxxxxxxxx-xxxxx                   1/1     Running   0          2m
argocd-notifications-controller-xxxxxxxxx-xxxxx     1/1     Running   0          2m
argocd-redis-xxxxxxxxx-xxxxx                        1/1     Running   0          2m
argocd-repo-server-xxxxxxxxx-xxxxx                  1/1     Running   0          2m
argocd-server-xxxxxxxxx-xxxxx                       1/1     Running   0          2m
```

### 5. Admin 초기 비밀번호 확인

ArgoCD는 처음 설치 시 자동으로 admin 비밀번호를 생성합니다:

```bash
# Admin 초기 비밀번호 확인
kubectl get secret argocd-initial-admin-secret -n argocd -o jsonpath="{.data.password}" | base64 -d && echo

# 또는 더 안전하게
kubectl get secret argocd-initial-admin-secret -n argocd -o yaml
```

**로그인 정보:**
- Username: `admin`
- Password: (위 명령어로 확인한 값)

### 6. Ingress 설정 (Traefik + TLS)

ArgoCD UI에 외부에서 접속하기 위해 Traefik IngressRoute를 설정합니다:

```bash
# Ingress 적용 (이미 준비된 파일)
kubectl apply -f infra/argocd/argocd-ingress.yaml

# Ingress 확인
kubectl get ingressroute -n argocd

# Certificate 확인 (자동 발급됨, 1-2분 소요)
kubectl get certificate -n argocd

# Certificate 상세 정보
kubectl describe certificate argocd-tls -n argocd
```

### 7. ArgoCD UI 접속

TLS 인증서가 발급되면 (READY=True) 브라우저에서 접속:
- URL: **https://argocd.tickget.kr**
- Username: `admin`
- Password: (초기 비밀번호)

⚠️ **첫 로그인 후 비밀번호를 변경하세요!**

## ArgoCD CLI 설치 (선택사항)

### Linux (EC2)

```bash
# ArgoCD CLI 다운로드 (ARM64)
curl -sSL -o argocd https://github.com/argoproj/argo-cd/releases/latest/download/argocd-linux-arm64

# 실행 권한 부여
chmod +x argocd

# /usr/local/bin으로 이동
sudo mv argocd /usr/local/bin/

# 버전 확인
argocd version --client
```

### CLI 로그인

```bash
# ArgoCD 서버에 로그인 (HTTPS)
argocd login argocd.tickget.kr --username admin

# 또는 kubectl port-forward 사용
kubectl port-forward svc/argocd-server -n argocd 8080:443 --address 0.0.0.0
argocd login localhost:8080 --username admin --insecure

# 비밀번호 변경
argocd account update-password
```

## GitHub Repository 연결

### HTTPS + Personal Access Token 방식 (권장)

#### UI에서 연결:
1. ArgoCD UI 접속 (https://argocd.tickget.kr)
2. Settings → Repositories → "Connect Repo"
3. 다음 정보 입력:
   - **Type**: git
   - **Repository URL**: `https://github.com/Tickget/tickget-k8s-manifest.git`
   - **Username**: (GitHub 사용자명)
   - **Password**: (GitHub Personal Access Token)
4. "Connect" 클릭

#### CLI로 연결:
```bash
argocd repo add https://github.com/Tickget/tickget-k8s-manifest.git \
  --username <github-username> \
  --password <github-personal-access-token> \
  --insecure-skip-server-verification
```

### 연결 확인

```bash
# CLI로 확인
argocd repo list

# 또는 kubectl로 확인
kubectl get secret -n argocd -l argocd.argoproj.io/secret-type=repository
```

## ArgoCD Application 배포

### Application 리소스 적용

이미 준비된 Application 리소스들을 배포합니다:

⚠️ **중요**: Application 리소스의 `repoURL`을 먼저 수정해야 합니다!

```bash
# 1. repoURL 수정 필요 확인
grep -r "lab.ssafy.com" argocd-apps/

# 2. 수정 후 적용
kubectl apply -f argocd-apps/

# 3. Application 확인
kubectl get applications -n argocd

# 또는 CLI로 확인
argocd app list
```

### UI에서 확인

ArgoCD UI (https://argocd.tickget.kr)에서:
1. **Applications** 메뉴 클릭
2. 배포된 애플리케이션 목록 확인
3. 각 애플리케이션의 상태 확인:
   - **Synced**: Git과 클러스터 상태 일치
   - **Healthy**: 모든 리소스 정상 동작

## Helm 업그레이드

### ArgoCD 버전 업그레이드

```bash
# 사용 가능한 Chart 버전 확인
helm search repo argo/argo-cd --versions

# 업그레이드 (기존 설정 유지)
helm upgrade argocd argo/argo-cd \
  --namespace argocd \
  --reuse-values

# 또는 values.yaml 파일 사용
helm upgrade argocd argo/argo-cd \
  --namespace argocd \
  --values infra/argocd/values.yaml

# 업그레이드 확인
helm list -n argocd
kubectl get pods -n argocd
```

### 설정 변경

```bash
# 특정 값만 변경
helm upgrade argocd argo/argo-cd \
  --namespace argocd \
  --reuse-values \
  --set server.replicas=2

# 현재 설정 확인
helm get values argocd -n argocd
```

## Helm 롤백

```bash
# Release 히스토리 확인
helm history argocd -n argocd

# 이전 버전으로 롤백
helm rollback argocd <revision-number> -n argocd

# 예: 이전 버전으로 롤백
helm rollback argocd 1 -n argocd
```

## Helm 삭제

```bash
# ArgoCD 완전 삭제 (주의!)
helm uninstall argocd -n argocd

# 네임스페이스 삭제 (선택사항)
kubectl delete namespace argocd
```

## 주요 기능

### 자동 동기화

Application 리소스에서 `syncPolicy.automated`가 활성화되어 있으면:
- Git 저장소의 변경사항을 자동으로 감지 (폴링 주기: 3분)
- 자동으로 클러스터에 반영
- `selfHeal: true`인 경우 클러스터의 수동 변경을 Git 상태로 되돌림

### 수동 동기화

```bash
# CLI로 수동 동기화
argocd app sync <application-name>

# 모든 애플리케이션 동기화
argocd app sync --all

# UI에서 수동 동기화
# Application 상세 화면 → "SYNC" 버튼 클릭
```

### 롤백

```bash
# 이전 버전으로 롤백 (CLI)
argocd app rollback <application-name> <revision-number>

# UI에서 롤백
# Application 상세 화면 → "HISTORY AND ROLLBACK" 탭 → 원하는 버전 선택 → "ROLLBACK"
```

## 트러블슈팅

### Pod가 Running 상태가 안 됨

```bash
# Pod 로그 확인
kubectl logs -n argocd -l app.kubernetes.io/name=argocd-server
kubectl logs -n argocd -l app.kubernetes.io/name=argocd-application-controller
kubectl logs -n argocd -l app.kubernetes.io/name=argocd-repo-server

# Helm Release 상태 확인
helm status argocd -n argocd
```

### Application이 Synced 상태가 안 됨

```bash
# Application 상세 정보 확인
argocd app get <application-name>

# 동기화 로그 확인
kubectl logs -n argocd -l app.kubernetes.io/name=argocd-application-controller --tail=100

# Application 이벤트 확인
kubectl describe application <application-name> -n argocd
```

### Git 저장소 연결 실패

```bash
# Repository 연결 상태 확인
argocd repo list

# 연결 테스트
argocd repo get https://github.com/Tickget/tickget-k8s-manifest.git

# Secret 확인
kubectl get secret -n argocd -l argocd.argoproj.io/secret-type=repository -o yaml
```

### Ingress 접속 안 됨

```bash
# IngressRoute 확인
kubectl get ingressroute -n argocd -o yaml

# Certificate 상태 확인
kubectl get certificate -n argocd
kubectl describe certificate argocd-tls -n argocd

# ArgoCD Server가 insecure 모드인지 확인
kubectl get cm argocd-cmd-params-cm -n argocd -o yaml
```

## 보안 설정

### Admin 비밀번호 변경

```bash
# CLI로 변경
argocd account update-password

# 또는 UI에서 변경
# User Info → Update Password
```

### 초기 비밀번호 Secret 삭제 (선택사항)

비밀번호를 변경한 후에는 초기 비밀번호 Secret을 삭제할 수 있습니다:

```bash
kubectl delete secret argocd-initial-admin-secret -n argocd
```

### RBAC 설정

ArgoCD는 기본적으로 admin 사용자만 존재합니다. 추가 사용자 및 권한 설정은 공식 문서를 참고하세요:
- https://argo-cd.readthedocs.io/en/stable/operator-manual/rbac/

## 고급 설정 (GitOps로 ArgoCD 관리)

ArgoCD를 ArgoCD 자신으로 관리하는 방법 (App of Apps 패턴):

```bash
# ArgoCD Application 리소스로 ArgoCD 자신을 관리
kubectl apply -f infra/argocd/argocd-helm-app.yaml

# 이후 ArgoCD 설정 변경은 Git을 통해서만 수행
# values.yaml 수정 → Git Push → ArgoCD 자동 동기화
```

이렇게 하면 ArgoCD 자체도 GitOps로 관리할 수 있습니다!

## 참고 자료

- 공식 문서: https://argo-cd.readthedocs.io/
- Helm Chart: https://github.com/argoproj/argo-helm/tree/main/charts/argo-cd
- 설치 가이드: https://argo-cd.readthedocs.io/en/stable/getting_started/
- UI 사용법: https://argo-cd.readthedocs.io/en/stable/user-guide/
- CLI 사용법: https://argo-cd.readthedocs.io/en/stable/user-guide/commands/argocd/

## 버전 정보

- ArgoCD Helm Chart: v7.x.x (latest stable)
- ArgoCD: v2.13.x
- Kubernetes: v1.33.5 (K3s)
- Helm: v3.x.x
- Git Repository: https://github.com/Tickget/tickget-k8s-manifest.git

## 파일 구조

```
infra/argocd/
├── README.md                 # 이 파일 (Helm 설치 가이드)
├── argocd-ingress.yaml      # Traefik IngressRoute (TLS 포함)
├── values.yaml              # Helm values 예시 (커스터마이징용)
└── argocd-helm-app.yaml     # ArgoCD를 ArgoCD로 관리하는 Application 리소스
```
