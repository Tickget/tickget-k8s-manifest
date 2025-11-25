#!/usr/bin/env python3
"""
MySQL concert_halls 테이블 데이터를 Elasticsearch로 인덱싱하는 스크립트
Kubernetes 환경에서 실행됨

사용법:
  python3 mysql-to-elasticsearch-indexing.py
"""

import json
import sys
import time
from datetime import datetime

try:
    import pymysql
    from elasticsearch import Elasticsearch, helpers
except ImportError:
    print("필요한 패키지를 설치합니다...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pymysql", "elasticsearch"])
    import pymysql
    from elasticsearch import Elasticsearch, helpers

# 설정
MYSQL_CONFIG = {
    'host': 'mysql-service.db.svc.cluster.local',  # Kubernetes 서비스 DNS
    'port': 3306,
    'user': 'tickget',
    'password': 'hiiiiky',
    'database': 'tickget_db',
    'charset': 'utf8mb4'
}

ES_CONFIG = {
    'hosts': ['http://elasticsearch-service.db.svc.cluster.local:9200'],
    'timeout': 30,
    'max_retries': 3,
    'retry_on_timeout': True
}

INDEX_NAME = 'concert-halls'
MAPPING_FILE = '/tmp/concert-halls-index-mapping.json'


def connect_mysql():
    """MySQL 연결"""
    try:
        connection = pymysql.connect(**MYSQL_CONFIG)
        print(f"✅ MySQL 연결 성공: {MYSQL_CONFIG['host']}")
        return connection
    except Exception as e:
        print(f"❌ MySQL 연결 실패: {e}")
        sys.exit(1)


def connect_elasticsearch():
    """Elasticsearch 연결"""
    try:
        es = Elasticsearch(**ES_CONFIG)
        if es.ping():
            print(f"✅ Elasticsearch 연결 성공: {ES_CONFIG['hosts'][0]}")
            return es
        else:
            raise Exception("Elasticsearch ping 실패")
    except Exception as e:
        print(f"❌ Elasticsearch 연결 실패: {e}")
        sys.exit(1)


def load_index_mapping():
    """인덱스 매핑 파일 로드"""
    try:
        with open(MAPPING_FILE, 'r', encoding='utf-8') as f:
            mapping = json.load(f)
        print(f"✅ 인덱스 매핑 로드 완료: {MAPPING_FILE}")
        return mapping
    except Exception as e:
        print(f"❌ 인덱스 매핑 로드 실패: {e}")
        sys.exit(1)


def create_index(es, mapping):
    """Elasticsearch 인덱스 생성"""
    try:
        # 기존 인덱스 삭제 (재생성)
        if es.indices.exists(index=INDEX_NAME):
            print(f"⚠️  기존 인덱스 삭제: {INDEX_NAME}")
            es.indices.delete(index=INDEX_NAME)

        # 새 인덱스 생성
        es.indices.create(index=INDEX_NAME, body=mapping)
        print(f"✅ 인덱스 생성 완료: {INDEX_NAME}")

    except Exception as e:
        print(f"❌ 인덱스 생성 실패: {e}")
        sys.exit(1)


def fetch_concert_halls(connection):
    """MySQL에서 concert_halls 데이터 조회"""
    try:
        with connection.cursor(pymysql.cursors.DictCursor) as cursor:
            query = "SELECT id, name, total_seat, created_at FROM concert_halls ORDER BY id"
            cursor.execute(query)
            results = cursor.fetchall()
            print(f"✅ MySQL 데이터 조회 완료: {len(results)}건")
            return results
    except Exception as e:
        print(f"❌ MySQL 데이터 조회 실패: {e}")
        sys.exit(1)


def generate_bulk_data(concert_halls):
    """Bulk API용 데이터 생성"""
    for hall in concert_halls:
        doc = {
            '_index': INDEX_NAME,
            '_id': str(hall['id']),
            '_source': {
                'name': hall['name'],
                'total_seat': hall['total_seat'],
                'created_at': hall['created_at'].strftime('%Y-%m-%d %H:%M:%S') if hall['created_at'] else None
            }
        }
        yield doc


def bulk_index(es, concert_halls):
    """Bulk API로 데이터 인덱싱"""
    try:
        print(f"\n🚀 데이터 인덱싱 시작 ({len(concert_halls)}건)...")
        start_time = time.time()

        # Bulk API 실행
        success, failed = helpers.bulk(
            es,
            generate_bulk_data(concert_halls),
            chunk_size=500,
            raise_on_error=False,
            stats_only=False
        )

        elapsed_time = time.time() - start_time

        print(f"\n✅ 인덱싱 완료:")
        print(f"   - 성공: {success}건")
        print(f"   - 실패: {len(failed) if isinstance(failed, list) else 0}건")
        print(f"   - 소요 시간: {elapsed_time:.2f}초")

        if failed:
            print(f"\n⚠️  실패한 문서:")
            for item in failed[:10]:  # 최대 10개만 표시
                print(f"   - ID: {item}")

    except Exception as e:
        print(f"❌ 인덱싱 실패: {e}")
        sys.exit(1)


def verify_indexing(es):
    """인덱싱 결과 확인"""
    try:
        # 인덱스 통계
        stats = es.indices.stats(index=INDEX_NAME)
        doc_count = stats['indices'][INDEX_NAME]['total']['docs']['count']

        print(f"\n📊 인덱싱 결과:")
        print(f"   - 인덱스: {INDEX_NAME}")
        print(f"   - 문서 수: {doc_count}건")

        # 샘플 검색 테스트
        response = es.search(
            index=INDEX_NAME,
            body={
                "query": {"match": {"name.ngram": "예술"}},
                "size": 3
            }
        )

        print(f"\n🔍 검색 테스트 (키워드: '예술'):")
        for hit in response['hits']['hits']:
            print(f"   - {hit['_source']['name']} (좌석: {hit['_source']['total_seat']})")

    except Exception as e:
        print(f"❌ 결과 확인 실패: {e}")


def main():
    print("=" * 60)
    print("MySQL → Elasticsearch 데이터 인덱싱")
    print("=" * 60)

    # 1. 연결
    mysql_conn = connect_mysql()
    es = connect_elasticsearch()

    # 2. 인덱스 매핑 로드 및 생성
    mapping = load_index_mapping()
    create_index(es, mapping)

    # 3. MySQL 데이터 조회
    concert_halls = fetch_concert_halls(mysql_conn)

    # 4. Elasticsearch 인덱싱
    bulk_index(es, concert_halls)

    # 5. 결과 확인
    verify_indexing(es)

    # 6. 연결 종료
    mysql_conn.close()
    print("\n✅ 모든 작업 완료!")
    print("=" * 60)


if __name__ == '__main__':
    main()
