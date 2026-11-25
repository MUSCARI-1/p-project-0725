// 백엔드 연결 확인용 임시 화면이다
import { useEffect, useRef, useState } from "react";
import { chat, getMeta, getPolicy, getRegions, recommend } from "./api.js";

const ELIGIBILITY = { eligible: "신청 가능", check_needed: "확인 필요", ineligible: "불가" };
const RESULT = { met: "✅", unmet: "❌", unknown: "❔" };

export default function App() {
  const [meta, setMeta] = useState(null);
  const [regions, setRegions] = useState([]);
  const [sido, setSido] = useState("11");
  const [form, setForm] = useState({
    birth_date: "1999-05-12",
    region_code: "11380",
    marital_status: "single",
    job_status: "unemployed",
    education: "university_enrolled",
    annual_income: "",
    message: "휴학 중이고 알바하는데 월세가 부담돼요",
  });
  const [categories, setCategories] = useState([]);
  const [data, setData] = useState(null);
  const [openId, setOpenId] = useState(null);
  const [error, setError] = useState("");
  const resultsRef = useRef(null);

  useEffect(() => {
    getMeta().then(setMeta).catch((e) => setError(e.message));
    getRegions().then((r) => setRegions(r.regions)).catch((e) => setError(e.message));
  }, []);

  const sidoItem = regions.find((r) => r.code === sido);
  const sigunguItem = sidoItem?.sigungu.find((s) => s.code === form.region_code);

  const update = (key) => (e) => setForm({ ...form, [key]: e.target.value });
  const toggle = (c) =>
    setCategories(categories.includes(c) ? categories.filter((x) => x !== c) : [...categories, c]);

  async function submit(e, page = 1) {
    e?.preventDefault();
    setError("");
    setOpenId(null);
    const profile = {
      ...form,
      region_code: form.region_code || null,
      region_name: sigunguItem ? `${sidoItem.name} ${sigunguItem.name}` : null,
      marital_status: form.marital_status || null,
      job_status: form.job_status || null,
      education: form.education || null,
      annual_income: form.annual_income === "" ? null : Number(form.annual_income),
      categories,
      page,
      size: 10,
    };
    try {
      setData(await recommend(profile));
      resultsRef.current?.scrollIntoView();
    } catch (err) {
      setError(err.message);
    }
  }

  const select = (key) => (
    <label>
      {key}{" "}
      <select value={form[key]} onChange={update(key)}>
        <option value="">(모름)</option>
        {meta?.enums[key].map((v) => (
          <option key={v}>{v}</option>
        ))}
      </select>
    </label>
  );

  return (
    <main style={{ maxWidth: 820, margin: "0 auto", padding: 16, fontFamily: "sans-serif" }}>
      <h1>청년 정책 AI 가이드 (연결 테스트)</h1>
      <p>정책 {meta?.policy_count ?? "-"}건 · 마지막 수집 {meta?.last_synced_at ?? "-"}</p>

      <form onSubmit={submit} style={{ display: "grid", gap: 8 }}>
        <label>
          birth_date <input type="date" value={form.birth_date} onChange={update("birth_date")} />
        </label>
        <label>
          region{" "}
          <select
            value={sido}
            onChange={(e) => {
              setSido(e.target.value);
              setForm({ ...form, region_code: "" });
            }}
          >
            <option value="">(전국)</option>
            {regions.map((r) => (
              <option key={r.code} value={r.code}>{r.name}</option>
            ))}
          </select>{" "}
          <select value={form.region_code} onChange={update("region_code")} disabled={!sidoItem}>
            <option value="">(선택 안 함)</option>
            {sidoItem?.sigungu.map((s) => (
              <option key={s.code} value={s.code}>{s.name} ({s.code})</option>
            ))}
          </select>
        </label>
        {select("marital_status")}
        {select("job_status")}
        {select("education")}
        <label>
          annual_income (만 원){" "}
          <input type="number" value={form.annual_income} onChange={update("annual_income")} placeholder="비우면 모름" />
        </label>
        <div>
          {meta?.enums.categories.map((c) => (
            <label key={c} style={{ marginRight: 8 }}>
              <input type="checkbox" checked={categories.includes(c)} onChange={() => toggle(c)} /> {c}
            </label>
          ))}
        </div>
        <textarea rows={2} value={form.message} onChange={update("message")} />
        <button>추천 받기</button>
      </form>

      {error && <p style={{ color: "crimson" }}>{error}</p>}

      {data && (
        <section ref={resultsRef}>
          <h2>
            후보 {data.total}건 (페이지 {data.page}, 이 페이지 {data.results.length}건)
          </h2>
          {data.results.map((r) => (
            <article key={r.policy_id} style={{ border: "1px solid #ccc", padding: 12, marginBottom: 8 }}>
              <strong>[{ELIGIBILITY[r.eligibility]}]</strong> {r.name}{" "}
              <small>
                {r.category} · {r.apply_status} · {r.apply_period}
              </small>
              <ul>
                {r.reasons.map((x, i) => (
                  <li key={i}>
                    {RESULT[x.result]} {x.condition}: {x.detail}
                  </li>
                ))}
              </ul>
              <button onClick={() => setOpenId(openId === r.policy_id ? null : r.policy_id)}>
                {openId === r.policy_id ? "닫기" : "상세 보기"}
              </button>
              {openId === r.policy_id && <Detail policyId={r.policy_id} sourceText={r.source_text} />}
            </article>
          ))}
          <button disabled={data.page <= 1} onClick={() => submit(null, data.page - 1)}>
            이전
          </button>
          <button disabled={data.page * data.size >= data.total} onClick={() => submit(null, data.page + 1)}>
            다음
          </button>
        </section>
      )}
    </main>
  );
}

function Detail({ policyId, sourceText }) {
  const [detail, setDetail] = useState(null);
  const [error, setError] = useState("");
  const [question, setQuestion] = useState("");
  const [history, setHistory] = useState([]);
  const [sources, setSources] = useState([]);

  useEffect(() => {
    getPolicy(policyId).then(setDetail).catch((e) => setError(e.message));
  }, [policyId]);

  async function ask(e) {
    e.preventDefault();
    if (!question.trim()) return;
    try {
      const res = await chat({ question, policy_id: policyId, history });
      setHistory([...history, { role: "user", content: question }, { role: "assistant", content: res.answer }]);
      setSources(res.sources);
      setQuestion("");
    } catch (err) {
      setError(err.message);
    }
  }

  if (error) return <p style={{ color: "crimson" }}>{error}</p>;
  if (!detail) return <p>불러오는 중...</p>;

  const c = detail.conditions;
  return (
    <div style={{ background: "#f6f6f6", padding: 12, marginTop: 8 }}>
      <p><b>지원 내용</b><br />{detail.support}</p>
      <p><b>신청 기간</b> {detail.apply_period || "-"} ({detail.apply_status})</p>
      <p><b>신청 방법</b><br />{detail.apply_method || "-"}</p>
      <p>
        {detail.apply_url && <a href={detail.apply_url} target="_blank" rel="noreferrer">신청 링크</a>}{" "}
        {detail.ref_url && <a href={detail.ref_url} target="_blank" rel="noreferrer">참고 링크</a>}
      </p>
      <b>제출 서류</b>
      {detail.documents.length ? (
        <ul>
          {detail.documents.map((d) => (
            <li key={d}><label><input type="checkbox" /> {d}</label></li>
          ))}
        </ul>
      ) : (
        <p>공고문 참조 (원문: {detail.documents_text || "없음"})</p>
      )}
      <p><b>나이</b> {c.min_age ?? "제한 없음"} ~ {c.max_age ?? "제한 없음"} · <b>대상 지역 수</b> {c.region_codes.length}</p>
      {c.extra_qualification && <p><b>추가 자격</b><br />{c.extra_qualification}</p>}
      {c.excluded_targets && <p><b>참여 제한 대상</b><br />{c.excluded_targets}</p>}
      {sourceText && <p><b>판단 근거 원문</b><br />{sourceText}</p>}

      <b>챗봇 테스트</b>
      {history.map((h, i) => (
        <p key={i}>{h.role === "user" ? "🙋" : "🤖"} {h.content}</p>
      ))}
      {sources.map((s, i) => (
        <p key={i} style={{ fontSize: 12, color: "#555" }}>📄 참고 원문: {s.text}</p>
      ))}
      <form onSubmit={ask} style={{ display: "flex", gap: 4 }}>
        <input style={{ flex: 1 }} value={question} onChange={(e) => setQuestion(e.target.value)} placeholder="예: 알바 소득도 포함돼요?" />
        <button>질문</button>
      </form>

      <details>
        <summary>응답 JSON 전체</summary>
        <pre style={{ whiteSpace: "pre-wrap" }}>{JSON.stringify(detail, null, 2)}</pre>
      </details>
    </div>
  );
}
