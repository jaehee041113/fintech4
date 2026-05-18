/**
 * components/SpendingForm.tsx — 지출 입력 폼 컴포넌트
 * =====================================================
 * 사용자가 카테고리별 월 지출 금액을 입력하는 폼입니다.
 * 카드 유형 필터, 추천 수 선택, 추천 요청 버튼도 포함합니다.
 *
 * 이 컴포넌트는 "presentational component" 패턴을 따릅니다:
 *   - 상태(state)를 직접 갖지 않습니다.
 *   - 모든 데이터와 핸들러를 props로 부모(page.tsx)에서 받습니다.
 *   - 입력이 바뀌면 onChange를 호출해 부모의 state를 업데이트합니다.
 *
 * Material Design 3 (M3) 디자인 가이드라인을 따릅니다:
 *   - Filter Chip: 카드 유형/추천 수 선택 버튼 (rounded-full 형태)
 *   - Outlined Text Field: 지출 금액 입력 필드
 *   - Filled Button: "카드 추천받기" 버튼 (rounded-full 형태)
 */
"use client";

import { CATEGORIES, Category } from "@/lib/api";

// ── Props 타입 정의 ───────────────────────────────────────
// 이 컴포넌트가 부모(page.tsx)로부터 받는 데이터와 함수의 타입
interface Props {
  spending:        Record<Category, number>;           // 카테고리별 지출 금액
  cardType:        "all" | "credit" | "debit";        // 선택된 카드 유형
  topN:            number;                             // 추천 카드 수
  loading:         boolean;                            // 로딩 중 여부
  onChange:        (category: Category, value: number) => void; // 지출 금액 변경 시
  onCardTypeChange: (v: "all" | "credit" | "debit") => void;   // 카드 유형 변경 시
  onTopNChange:    (v: number) => void;                // 추천 수 변경 시
  onSubmit:        () => void;                         // 추천 요청 버튼 클릭 시
}

// 카테고리 내부 이름 → 화면에 표시할 라벨 매핑
const CATEGORY_LABELS: Record<Category, string> = {
  전가맹점:      "전 가맹점",
  "음식/카페":   "음식 / 카페",
  "주유/교통":   "주유 / 교통",
  "쇼핑/간편결제": "쇼핑 / 간편결제",
  "항공/해외":   "항공 / 해외",
  "교육/건강":   "교육 / 건강",
  자동납부:      "자동납부",
  통신:          "통신",
  "Biz/공공":   "Biz / 공공",
};

export default function SpendingForm({
  spending,
  cardType,
  topN,
  loading,
  onChange,
  onCardTypeChange,
  onTopNChange,
  onSubmit,
}: Props) {
  // 모든 카테고리 지출 합계 (총 지출액 표시 + 버튼 비활성화 조건)
  const total = Object.values(spending).reduce((a, b) => a + b, 0);

  return (
    <div className="rounded-2xl border border-black/[0.12] bg-white p-6">

      {/* 폼 제목 */}
      <h2 className="mb-5 text-base font-semibold tracking-wide text-zinc-800">
        월 지출 금액 입력
      </h2>

      {/* ── 카테고리별 지출 입력 필드 ─────────────────────── */}
      {/* grid: 반응형 열 배치 (모바일 1열 → 태블릿 2열 → PC 3열) */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {CATEGORIES.map((cat) => (
          <div key={cat} className="flex flex-col gap-1.5">
            {/* 카테고리 라벨 */}
            <label className="text-xs font-medium text-zinc-500">
              {CATEGORY_LABELS[cat]}
            </label>

            {/* 금액 입력 필드 (M3 Outlined Text Field 스타일) */}
            <div className="relative">
              <input
                type="number"
                min={0}
                step={10000}          // 스크롤/화살표 키로 10,000원 단위 조정
                value={spending[cat] === 0 ? "" : spending[cat]} // 0이면 빈 칸 표시
                placeholder="0"
                onChange={(e) =>
                  // Math.max(0, ...): 음수 입력 방지
                  onChange(cat, Math.max(0, Number(e.target.value)))
                }
                className="w-full rounded-lg border border-zinc-300 py-2.5 pl-3 pr-8 text-sm text-zinc-800 placeholder-zinc-300 transition-colors focus:border-[#ffcc00] focus:outline-none focus:ring-1 focus:ring-[#ffcc00]"
              />
              {/* 입력 필드 우측 "원" 단위 표시 */}
              <span className="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-zinc-400">
                원
              </span>
            </div>
          </div>
        ))}
      </div>

      {/* ── 필터 및 추천 버튼 영역 ─────────────────────────── */}
      <div className="mt-6 flex flex-wrap items-center gap-4 border-t border-zinc-100 pt-5">

        {/* 카드 유형 선택 (M3 Filter Chip) */}
        <div className="flex items-center gap-2">
          <span className="text-xs font-medium text-zinc-500">카드 유형</span>
          {(["all", "credit", "debit"] as const).map((t) => (
            <button
              key={t}
              onClick={() => onCardTypeChange(t)}
              className={`min-h-[32px] rounded-full px-4 py-1 text-xs font-medium transition-colors ${
                cardType === t
                  ? "bg-[#ffcc00] text-zinc-900"           // 선택된 상태: KB 노란색
                  : "border border-zinc-300 bg-white text-zinc-600 hover:bg-zinc-50" // 미선택 상태
              }`}
            >
              {t === "all" ? "전체" : t === "credit" ? "신용" : "체크"}
            </button>
          ))}
        </div>

        {/* 추천 카드 수 선택 (M3 Filter Chip) */}
        <div className="flex items-center gap-2">
          <span className="text-xs font-medium text-zinc-500">추천 수</span>
          {[3, 5, 10].map((n) => (
            <button
              key={n}
              onClick={() => onTopNChange(n)}
              className={`min-h-[32px] rounded-full px-4 py-1 text-xs font-medium transition-colors ${
                topN === n
                  ? "bg-[#ffcc00] text-zinc-900"
                  : "border border-zinc-300 bg-white text-zinc-600 hover:bg-zinc-50"
              }`}
            >
              {n}개
            </button>
          ))}
        </div>

        {/* 총 지출 + 추천 요청 버튼 */}
        <div className="ml-auto flex items-center gap-3">
          {/* 총 지출 금액 표시 */}
          <span className="text-sm text-zinc-500">
            총{" "}
            <span className="font-semibold text-zinc-800">
              {total.toLocaleString()} {/* toLocaleString: 숫자에 쉼표 추가 (300000 → 300,000) */}
            </span>
            원
          </span>

          {/* 추천 요청 버튼 (M3 Filled Button) */}
          <button
            onClick={onSubmit}
            disabled={loading || total === 0} // 로딩 중이거나 지출 합계가 0이면 비활성화
            className="rounded-full bg-[#ffcc00] px-6 py-2.5 text-sm font-semibold text-zinc-900 transition-colors hover:bg-[#e6b800] disabled:cursor-not-allowed disabled:opacity-40"
          >
            {loading ? "분석 중..." : "카드 추천받기"}
          </button>
        </div>
      </div>
    </div>
  );
}
