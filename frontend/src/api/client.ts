import axios from "axios";

// Dev: frontend runs on the Vite dev server (:5173) talking to the FastAPI
// dev server on :8000. Prod (packaged exe): both are served from the same
// FastAPI process/port, so a relative path is enough.
export const api = axios.create({
  baseURL: import.meta.env.PROD ? "/api" : "http://127.0.0.1:8000/api",
});

api.interceptors.response.use(
  (res) => res,
  (err) => {
    const detail = err?.response?.data?.detail;
    const message = typeof detail === "string" ? detail : err.message;
    return Promise.reject(new Error(message));
  }
);
