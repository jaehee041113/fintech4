/**
 * app/api/recommend/route.ts — Next.js 서버사이드 프록시
 * =========================================================
 * 브라우저에서 백엔드(Docker 내부 네트워크)로 직접 요청할 수 없는 문제를 해결합니다.
 *
 * 문제 상황:
 *   브라우저 → http://backend:8000/api/recommend  ← 실패!
 *   (브라우저는 Docker 내부 네트워크의 "backend" 호스트명을 알 수 없음)
 *
 * 해결 방법 (서버사이드 프록시):
 *   브라우저 → /api/recommend (Next.js 서버) → http://backend:8000/api/recommend (FastAPI)
 *
 * 이 파일은 Next.js의 App Router Route Handler입니다.
 * POST /api/recommend 요청이 오면 이 파일의 POST 함수가 실행됩니다.
 *
 * 환경변수 BACKEND_URL:
 *   - Docker 환경 : docker-compose.yml에서 BACKEND_URL=http://backend:8000 주입
 *   - 로컬 환경   : 설정 없으면 기본값 "http://backend:8000" 사용
 */

import { NextRequest, NextResponse } from "next/server";

// 백엔드 URL: 환경변수에서 읽거나 기본값 사용
// process.env는 서버 사이드에서만 동작 (브라우저에서는 접근 불가)
const BACKEND = process.env.BACKEND_URL ?? "http://backend:8000";

/**
 * POST /api/recommend 요청 처리
 *
 * 처리 순서:
 *   1. 브라우저로부터 받은 JSON 요청 body 파싱
 *   2. 백엔드(FastAPI)로 동일한 body를 전달하여 요청
 *   3. 백엔드 응답을 그대로 브라우저에 전달
 *   4. 오류 발생 시 사람이 읽기 쉬운 에러 메시지로 변환
 */
export async function POST(req: NextRequest) {
  try {
    // 1단계: 브라우저 요청에서 JSON body 추출
    const body = await req.json();

    // 2단계: 백엔드로 프록시 요청
    const res = await fetch(`${BACKEND}/api/recommend`, {
      method:  "POST",
      headers: { "Content-Type": "application/json" },
      body:    JSON.stringify(body),
    });

    // 3단계: 백엔드 응답을 텍스트로 먼저 읽음
    // (JSON이 아닐 수 있으므로 텍스트로 먼저 받아서 파싱 시도)
    const text = await res.text();

    try {
      // JSON으로 파싱 성공 시: 그대로 브라우저에 전달
      const data = JSON.parse(text);
      return NextResponse.json(data, { status: res.status });
    } catch {
      // JSON 파싱 실패 시: 백엔드가 HTML 오류 페이지 등을 반환한 경우
      // 앞 200자만 잘라서 에러 메시지로 전달
      return NextResponse.json(
        { detail: `백엔드 오류: ${text.slice(0, 200)}` },
        { status: res.status }
      );
    }
  } catch (e) {
    // 백엔드 서버 자체에 연결할 수 없는 경우 (서버 다운, 네트워크 오류 등)
    return NextResponse.json(
      { detail: `서버 연결 실패: ${e}` },
      { status: 502 }  // 502 Bad Gateway: 프록시 서버가 업스트림 서버에 연결 실패
    );
  }
}
