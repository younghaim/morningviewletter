# Morning View Letter

매일 아침 발행하는 트렌드 뉴스레터 **Morning View Letter**의 웹 아카이브입니다.

- 사이트: https://younghaim.github.io/morningviewletter/
- 발행 편성: 월 AI · 화 K-Wave · 수 Wellness · 목 Business · 금 Market, 비정기 Deep View

## 새 호 올리는 법
1. `content/` 에 원고 파일을 추가합니다 (예: `vol-013.md`, Deep View는 `no-05.md`).
2. `python3 build.py` 를 실행하면 `issues/` 의 각 호 페이지와 `index.html` 목차가 다시 만들어집니다.
3. 커밋하고 `main` 에 푸시하면 1~2분 뒤 사이트에 반영됩니다.

원고 맨 위에는 아래 정보를 적습니다.

```
---
id: vol-013
kind: daily
section: AI          # AI | K-Wave | Wellness | Business | Market | Trend Note | Seminar Note
date: 2026-10-26
weekday: 월
read_time: 5분
title: 제목
lead: 첫 문단 한 줄 (없으면 비워 둠)
---
```

사이트는 공개됩니다. 비공개 강연·내부 자료에서 온 내용은 원고에 넣지 않습니다.
