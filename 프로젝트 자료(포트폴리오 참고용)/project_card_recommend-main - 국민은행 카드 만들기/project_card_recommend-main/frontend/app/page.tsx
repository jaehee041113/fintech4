/**
 * app/page.tsx — 메인 페이지 (홈 화면)
 * ========================================
 * 이 파일이 http://localhost:3000에 접속했을 때 보이는 화면입니다.
 *
 * 화면 구성:
 *   ┌─────────────────────────────┐
 *   │ 헤더 (KB국민카드 로고 + 제목) │
 *   ├─────────────────────────────┤
 *   │ SpendingForm (지출 입력 폼)  │
 *   ├─────────────────────────────┤
 *   │ 로딩 스피너 (분석 중)        │
 *   │ 에러 메시지                  │
 *   │ CardResult 목록 (추천 결과)  │
 *   └─────────────────────────────┘
 *
 * 상태(state) 관리:
 *   spending  - 카테고리별 지출 금액 입력값
 *   cardType  - 카드 유형 필터 (전체/신용/체크)
 *   topN      - 추천 카드 수
 *   loading   - API 호출 중 여부
 *   results   - 추천 결과 목록
 *   error     - 에러 메시지
 *   submitted - 한 번이라도 추천 요청을 했는지 여부
 *
 * "use client": 이 파일은 클라이언트 컴포넌트로 동작합니다.
 *   → useState, 이벤트 핸들러 등 브라우저 기능을 사용하기 위해 필요
 *   → 서버 컴포넌트(기본값)는 이런 기능을 사용할 수 없습니다.
 */
"use client";

import { useState } from "react";
import Image from "next/image";
import SpendingForm from "@/components/SpendingForm";
import CardResult from "@/components/CardResult";
import {
  CATEGORIES,
  Category,
  RecommendResult,
  fetchRecommendations,
} from "@/lib/api";

// 초기 지출 금액: 모든 카테고리를 0으로 초기화
// Object.fromEntries: [["전가맹점", 0], ["음식/카페", 0], ...] → {전가맹점: 0, 음식/카페: 0, ...}
const initialSpending = Object.fromEntries(
  CATEGORIES.map((c) => [c, 0])
) as Record<Category, number>;

export default function Home() {
  // ── 상태(State) 정의 ─────────────────────────────────────
  // useState: React에서 화면에 영향을 주는 변수를 관리하는 훅
  // 값이 바뀔 때마다 화면이 자동으로 다시 렌더링됩니다.

  const [spending,  setSpending]  = useState<Record<Category, number>>(initialSpending);
  const [cardType,  setCardType]  = useState<"all" | "credit" | "debit">("all");
  const [topN,      setTopN]      = useState(5);
  const [loading,   setLoading]   = useState(false);
  const [results,   setResults]   = useState<RecommendResult[]>([]);
  const [error,     setError]     = useState<string | null>(null);
  const [submitted, setSubmitted] = useState(false); // 결과 없음 메시지 표시 조건에 사용

  // ── 이벤트 핸들러 ─────────────────────────────────────────

  /**
   * 지출 금액 변경 핸들러
   * SpendingForm의 각 입력 필드가 바뀔 때 호출됩니다.
   */
  const handleChange = (category: Category, value: number) => {
    // 기존 spending 객체를 복사하고 해당 카테고리 값만 업데이트
    setSpending((prev) => ({ ...prev, [category]: value }));
  };

  /**
   * 추천 요청 핸들러
   * "카드 추천받기" 버튼 클릭 시 호출됩니다.
   *
   * 처리 순서:
   *   1. 로딩 상태 ON, 에러 초기화
   *   2. fetchRecommendations() 호출 → /api/recommend로 POST 요청
   *   3. 성공 시: results 상태 업데이트 → CardResult 목록 표시
   *   4. 실패 시: error 상태 업데이트 → 에러 메시지 표시
   *   5. 로딩 상태 OFF
   */
  const handleSubmit = async () => {
    setLoading(true);
    setError(null);
    setSubmitted(true);
    try {
      const res = await fetchRecommendations(
        spending,
        cardType === "all" ? null : cardType, // "all"은 null로 변환 (백엔드에서 전체 조회)
        topN
      );
      setResults(res.recommendations);
    } catch (e) {
      setError(e instanceof Error ? e.message : "오류가 발생했습니다.");
      setResults([]);
    } finally {
      // 성공/실패 관계없이 항상 로딩 상태 해제
      setLoading(false);
    }
  };

  // ── 화면 렌더링 ───────────────────────────────────────────
  return (
    <div className="min-h-screen bg-zinc-50">

      {/* ── 헤더 ────────────────────────────────────────── */}
      <header className="border-b border-zinc-200 bg-white">
        <div className="mx-auto max-w-4xl px-4 py-4">
          <div className="flex items-center gap-2">
            {/* KB국민카드 로고 이미지 */}
            <div className="relative h-8 w-24">
              <Image
                src="https://img1.kbcard.com/LT/images_r/common/kbcard_Logo_v3.png"
                alt="KB국민카드 로고"
                fill                    // 부모 div 크기에 맞게 채움
                className="object-contain"
                unoptimized             // Next.js 이미지 최적화 비활성화 (외부 URL)
              />
            </div>
            <div>
              <h1 className="text-base font-bold text-zinc-900">
                KB국민카드 추천
              </h1>
              <p className="text-xs text-zinc-500">
                지출 패턴 기반 최적 카드 추천
              </p>
            </div>
          </div>
        </div>
      </header>

      {/* ── 메인 콘텐츠 ─────────────────────────────────── */}
      <main className="mx-auto max-w-4xl px-4 py-6 flex flex-col gap-6">

        {/* 지출 입력 폼 */}
        {/* SpendingForm에 상태값과 핸들러를 props로 전달 */}
        <SpendingForm
          spending={spending}
          cardType={cardType}
          topN={topN}
          loading={loading}
          onChange={handleChange}
          onCardTypeChange={setCardType}
          onTopNChange={setTopN}
          onSubmit={handleSubmit}
        />

        {/* 로딩 중 스피너 */}
        {loading && (
          <div className="flex flex-col items-center gap-3 py-16 text-zinc-400">
            {/* animate-spin: Tailwind CSS 회전 애니메이션 */}
            <div className="h-8 w-8 animate-spin rounded-full border-2 border-zinc-200 border-t-[#ffcc00]" />
            <p className="text-sm">카드를 분석하는 중입니다...</p>
          </div>
        )}

        {/* 에러 메시지 */}
        {error && (
          <div className="rounded-xl border border-red-100 bg-red-50 px-5 py-4 text-sm text-red-600">
            {error}
          </div>
        )}

        {/* 결과 없음 메시지 (추천 요청 후 결과가 0개인 경우) */}
        {!loading && submitted && results.length === 0 && !error && (
          <div className="py-16 text-center text-sm text-zinc-400">
            조건에 맞는 카드가 없습니다.
          </div>
        )}

        {/* 추천 카드 목록 */}
        {!loading && results.length > 0 && (
          <div className="flex flex-col gap-4">
            <p className="text-sm font-medium text-zinc-500">
              추천 카드{" "}
              <span className="font-bold text-zinc-800">{results.length}개</span>
            </p>
            {/* results 배열을 순회하며 CardResult 컴포넌트 렌더링 */}
            {results.map((r) => (
              // key: React가 목록 항목을 구분하기 위해 필요한 고유값
              <CardResult key={r.card.cooperation_code} result={r} />
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
