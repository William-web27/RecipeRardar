import { api } from "./api";

const RETRY_STATUSES = new Set([404, 502, 503, 504]);
const FRIENDLY = "AI is briefly unavailable — please try again in a moment.";

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

/**
 * Call an API method with one retry on transient failures
 * (ingress 404 during hot-reload, LLM 502/503/504, network errors).
 * Always throws an Error with a friendly `.message` on final failure —
 * never leaks axios's raw "Request failed with status code NNN".
 */
export async function callAiApi(method, url, data, { tries = 2, delay = 900 } = {}) {
  let last;
  for (let i = 0; i < tries; i++) {
    try {
      const res = await api.request({ method, url, data });
      return res.data;
    } catch (e) {
      last = e;
      const status = e?.response?.status;
      const shouldRetry = !status || RETRY_STATUSES.has(status);
      if (!shouldRetry || i >= tries - 1) break;
      await sleep(delay * (i + 1));
    }
  }
  const detail = last?.response?.data?.detail;
  const status = last?.response?.status;
  const friendly = detail || (RETRY_STATUSES.has(status) || !status ? FRIENDLY : detail) || FRIENDLY;
  const err = new Error(friendly);
  err.status = status;
  err.original = last;
  throw err;
}
