def print_summary(site: str, count: int, file_path: str) -> None:
    print(f"[{site}] 수집 완료")
    print(f"- 수집 건수: {count}")
    print(f"- 저장 경로: {file_path}")