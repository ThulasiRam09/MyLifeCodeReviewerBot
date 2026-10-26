import React, { useEffect, useRef, useState } from "react";
import { streamReview, resetConversation } from "./api";
import MessageBubble from "./components/MessageBubble";
import { LANGUAGES } from "./languages";

const uid = () => Math.random().toString(36).slice(2, 9) + Date.now().toString(36);

export default function App() {
  const [messages, setMessages] = useState([]);
  const [problem, setProblem] = useState("");
  const [code, setCode] = useState("");
  const [language, setLanguage] = useState("Java");
  const [streaming, setStreaming] = useState(false);
  const [error, setError] = useState(null);
  const [conversationId, setConversationId] = useState("default");
  const abortRef = useRef(null);
  const scrollRef = useRef(null);
  const problemRef = useRef(null);
  const codeRef = useRef(null);

  useEffect(() => {
    const el = scrollRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [messages]);

  useEffect(() => {
    const ta = codeRef.current;
    if (ta) {
      ta.style.height = "auto";
      ta.style.height = Math.min(ta.scrollHeight, 220) + "px";
    }
  }, [code]);

  useEffect(() => {
    const ta = problemRef.current;
    if (ta) {
      ta.style.height = "auto";
      ta.style.height = Math.min(ta.scrollHeight, 120) + "px";
    }
  }, [problem]);

  async function send() {
    const codeText = code.trim();
    const probText = problem.trim();
    if ((!codeText && !probText) || streaming) return;
    const displayContent = probText
      ? `**Problem:**\n${probText}\n\n**Code (${language}):**\n\`\`\`${language.toLowerCase()}\n${codeText}\n\`\`\``
      : codeText;
    const userMsg = { id: uid(), role: "user", content: displayContent, language };
    const botId = uid();
    const botMsg = { id: botId, role: "assistant", content: "", streaming: true };
    setMessages((prev) => [...prev, userMsg, botMsg]);
    setCode("");
    setProblem("");
    setError(null);
    setStreaming(true);
    const controller = new AbortController();
    abortRef.current = controller;

    const updateBot = (patch) =>
      setMessages((prev) =>
        prev.map((m) => (m.id === botId ? { ...m, ...patch } : m))
      );

    try {
      await streamReview({
        code: codeText,
        language,
        problem: probText,
        conversationId,
        noSearch: false,
        signal: controller.signal,
        onToken: (t) =>
          setMessages((prev) =>
            prev.map((m) =>
              m.id === botId ? { ...m, content: (m.content || "") + t } : m
            )
          ),
        onDone: () => {
          updateBot({ streaming: false });
          setStreaming(false);
        },
        onError: (e) => {
          updateBot({ streaming: false });
          setStreaming(false);
          setError(typeof e === "string" ? e : "Review failed.");
        },
      });
    } catch (e) {
      if (e?.name !== "AbortError") {
        setError("Could not reach the reviewer backend. Start it with `uvicorn server.main:app --reload` from the project root and set GEMINI_API_KEY.");
      }
      updateBot({ streaming: false });
      setStreaming(false);
    }
  }

  async function newChat() {
    await resetConversation(conversationId);
    setConversationId(Math.random().toString(36).slice(2, 10));
    setMessages([]);
    setProblem("");
    setCode("");
    setError(null);
  }

  function stop() {
    abortRef.current?.abort();
  }

  return (
    <div className="app">
      <header className="app-header">
        <div className="header-inner">
          <div className="brand">
            <div className="brand-badge">{"</>"}</div>
            <div>
              <h1>MyLifeCodeReviewer</h1>
              <p>AI Code Reviewer · DSA Mentor · Interview Coach</p>
            </div>
          </div>
          <button type="button" className="btn ghost" onClick={newChat}>
            + New chat
          </button>
        </div>
      </header>

      <main className="chat" ref={scrollRef}>
        <div className="chat-inner">
          {messages.length === 0 ? (
            <div className="empty">
              <div className="empty-badge">{"</>"}</div>
              <h2>Review your code like an expert interviewer</h2>
              <p>
                Paste your DSA problem and solution below. The AI will review it,
                rate it out of 5, explore all better approaches, analyze time &amp;
                space complexity, and reveal which companies ask it.
              </p>
              <div className="chips">
                <span className="chip">Full code review</span>
                <span className="chip">Rating /5</span>
                <span className="chip">All approaches</span>
                <span className="chip">Time &amp; space complexity</span>
                <span className="chip">Company insights</span>
                <span className="chip">Test cases &amp; dry runs</span>
              </div>
            </div>
          ) : (
            messages.map((m) => <MessageBubble key={m.id} message={m} />)
          )}
          {error && <div className="error-banner">{error}</div>}
        </div>
      </main>

      <footer className="composer-wrap">
        <div className="composer">
          <div className="composer-fields">
            <textarea
              ref={problemRef}
              className="composer-problem"
              value={problem}
              onChange={(e) => setProblem(e.target.value)}
              placeholder={"Problem statement (optional)...\nDescribe the problem, constraints, examples if any."}
              rows={2}
            />
            <textarea
              ref={codeRef}
              className="composer-code"
              value={code}
              onChange={(e) => setCode(e.target.value)}
              placeholder={"Paste your solution code here...\n\n```" + language.toLowerCase() + "\n// your code here\n```"}
              rows={6}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  send();
                }
              }}
            />
          </div>
          <div className="composer-row">
            <div className="lang-wrap">
              <span className="lang-label">Language</span>
              <select value={language} onChange={(e) => setLanguage(e.target.value)}>
                {LANGUAGES.map((l) => (
                  <option key={l} value={l}>
                    {l}
                  </option>
                ))}
              </select>
            </div>
            {streaming ? (
              <button type="button" className="btn danger" onClick={stop}>
                ■ Stop
              </button>
            ) : (
              <button type="button" className="btn primary" onClick={send} disabled={!code.trim() && !problem.trim()}>
                Review Code
              </button>
            )}
          </div>
        </div>
        <p className="composer-hint">
          Enter to send · Shift+Enter for newline · Supports Java, Python, JavaScript, TypeScript, SQL, C#, C++, C, Go, Rust, PHP, Swift, Kotlin, R, Ruby
        </p>
      </footer>
    </div>
  );
}
