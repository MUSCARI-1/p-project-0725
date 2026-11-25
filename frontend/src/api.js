// 비워두면 개발 중에는 vite proxy를 쓴다. 배포 때 백엔드 주소를 넣는다.
const BASE = import.meta.env.VITE_API_BASE ?? "";

async function request(path, options = {}) {
  const res = await fetch(BASE + path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const body = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(body.message || `요청 실패 (${res.status})`);
  }
  return body;
}

export const getMeta = () => request("/api/meta");

export const getRegions = () => request("/api/regions");

export const recommend = (profile) =>
  request("/api/recommend", { method: "POST", body: JSON.stringify(profile) });

export const getPolicy = (policyId) => request(`/api/policies/${encodeURIComponent(policyId)}`);

export const searchPolicies = (params = {}) =>
  request(`/api/policies?${new URLSearchParams(params)}`);

export const chat = ({ question, policy_id, history = [] }) =>
  request("/api/chat", { method: "POST", body: JSON.stringify({ question, policy_id, history }) });
