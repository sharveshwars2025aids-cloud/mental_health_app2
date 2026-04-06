import { useState, useEffect, useRef } from "react";

const USER_ID = "frontend_user";
const API = "http://127.0.0.1:8002";

export default function App() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [listening, setListening] = useState(false);
  const [isTyping, setIsTyping] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [sessions, setSessions] = useState([]);
  const [currentSessionId, setCurrentSessionId] = useState(null);
  const [showConfirm, setShowConfirm] = useState(false);
  const messagesEndRef = useRef(null);

  // AUTO SCROLL
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isTyping]);

  // LOAD SESSIONS on mount
  useEffect(() => {
    fetchSessions();
  }, []);

  const fetchSessions = async () => {
    try {
      const res = await fetch(`${API}/sessions/${USER_ID}`);
      const data = await res.json();
      setSessions(data.sessions || []);
    } catch (err) {
      console.error("Failed to fetch sessions", err);
    }
  };

  // LOAD HISTORY for a session
  const loadSession = async (sessionId) => {
    try {
      const res = await fetch(`${API}/history/${sessionId}`);
      const data = await res.json();
      setMessages(data.messages || []);
      setCurrentSessionId(sessionId);
    } catch (err) {
      console.error("Failed to load session", err);
    }
  };

  // CREATE NEW SESSION
  const createNewSession = async () => {
    try {
      const res = await fetch(`${API}/sessions/new`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: USER_ID }),
      });
      const data = await res.json();
      setCurrentSessionId(data.session_id);
      setMessages([]);
      await fetchSessions();
    } catch (err) {
      console.error("Failed to create session", err);
    }
  };

  // NEW CHAT BUTTON — confirm if current chat has messages
  const handleNewChat = () => {
    if (messages.length > 0) {
      setShowConfirm(true);
    } else {
      createNewSession();
    }
  };

  // DELETE SESSION
  const deleteSession = async (sessionId, e) => {
    e.stopPropagation();
    try {
      await fetch(`${API}/sessions/${sessionId}`, { method: "DELETE" });
      if (sessionId === currentSessionId) {
        setMessages([]);
        setCurrentSessionId(null);
      }
      await fetchSessions();
    } catch (err) {
      console.error("Failed to delete session", err);
    }
  };

  // CLEAN TEXT
  const cleanText = (text) => {
    return text.replace(/[*_#]/g, "").replace(/[^\w\s.,!?]/g, "");
  };

  // SPEAK
  const speak = (text) => {
    if (!text) return;
    speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(cleanText(text));
    speechSynthesis.speak(utterance);
  };

  // MIC
  const startMic = () => {
    const SpeechRecognition =
      window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      alert("Use Chrome for voice input");
      return;
    }
    const rec = new SpeechRecognition();
    rec.lang = "en-IN";
    rec.interimResults = true;
    setListening(true);
    rec.start();
    rec.onresult = (e) => {
      let transcript = "";
      for (let i = 0; i < e.results.length; i++) {
        transcript += e.results[i][0].transcript;
      }
      setInput(transcript);
    };
    rec.onend = () => setListening(false);
    rec.onerror = () => setListening(false);
  };

  // SEND
  const sendMessage = async () => {
    if (!input.trim()) return;

    // Auto-create a session if none exists
    let sessionId = currentSessionId;
    if (!sessionId) {
      try {
        const res = await fetch(`${API}/sessions/new`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ user_id: USER_ID }),
        });
        const data = await res.json();
        sessionId = data.session_id;
        setCurrentSessionId(sessionId);
      } catch (err) {
        console.error("Failed to create session", err);
        return;
      }
    }

    const userMsg = input;
    setMessages((prev) => [...prev, { role: "user", content: userMsg }]);
    setInput("");
    setIsTyping(true);

    try {
      const res = await fetch(`${API}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_id: USER_ID,
          session_id: sessionId,
          user_message: userMsg,
        }),
      });
      const data = await res.json();
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: data.reply },
      ]);
      // Refresh sidebar titles after first message
      await fetchSessions();
    } catch (err) {
      console.error(err);
    }

    setIsTyping(false);
  };

  return (
    <div className="relative h-screen flex overflow-hidden">

      {/* BACKGROUND */}
      <div className="absolute inset-0 bg-gradient-to-br from-[#dbeafe] via-[#e0f2fe] to-[#ecfdf5]" />
      <div className="absolute w-72 h-72 bg-pink-300 opacity-30 rounded-full blur-3xl top-10 left-10 animate-pulse" />
      <div className="absolute w-72 h-72 bg-blue-300 opacity-30 rounded-full blur-3xl bottom-10 right-10 animate-pulse" />
      <div className="absolute w-60 h-60 bg-green-300 opacity-20 rounded-full blur-3xl top-1/2 left-1/3 animate-pulse" />

      {/* SIDEBAR */}
      <div
        className={`relative z-20 flex flex-col transition-all duration-300 ease-in-out
          ${sidebarOpen ? "w-64" : "w-0 overflow-hidden"}
          backdrop-blur-xl bg-white/40 border-r border-white/30 shadow-xl`}
      >
        {/* Sidebar Header */}
        <div className="p-4 flex items-center justify-between border-b border-white/30">
          <span className="font-semibold text-gray-700 text-sm">Conversations</span>
          <button
            onClick={handleNewChat}
            className="text-xs bg-green-500 text-white px-3 py-1 rounded-lg hover:bg-green-600 transition"
          >
            + New
          </button>
        </div>

        {/* Session List */}
        <div className="flex-1 overflow-y-auto p-2 space-y-1">
          {sessions.length === 0 && (
            <p className="text-xs text-gray-400 text-center mt-6 px-2">
              No conversations yet. Start chatting!
            </p>
          )}
          {sessions.map((s) => (
            <div
              key={s.session_id}
              onClick={() => loadSession(s.session_id)}
              className={`group flex items-center justify-between px-3 py-2 rounded-xl cursor-pointer transition
                ${currentSessionId === s.session_id
                  ? "bg-green-100/80 text-green-800 shadow-sm"
                  : "hover:bg-white/60 text-gray-700"
                }`}
            >
              <span className="text-xs truncate flex-1 pr-2">{s.title}</span>
              <button
                onClick={(e) => deleteSession(s.session_id, e)}
                className="opacity-0 group-hover:opacity-100 text-red-400 hover:text-red-600 text-xs transition"
                title="Delete"
              >
                ✕
              </button>
            </div>
          ))}
        </div>
      </div>

      {/* MAIN CONTENT */}
      <div className="relative z-10 flex flex-col flex-1 min-w-0">

        {/* HEADER */}
        <div className="p-4 flex items-center gap-3 backdrop-blur-lg bg-white/40 border-b border-white/30 shadow-md">
          <button
            onClick={() => setSidebarOpen((v) => !v)}
            className="text-gray-600 hover:text-gray-900 transition text-lg"
            title="Toggle sidebar"
          >
            ☰
          </button>
          <span className="text-xl font-semibold text-gray-700">🌿 MindEase</span>
        </div>

        {/* CHAT AREA */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">

          {/* Empty state */}
          {messages.length === 0 && !isTyping && (
            <div className="flex flex-col items-center justify-center h-full text-center text-gray-400 space-y-2">
              <div className="text-4xl">🌿</div>
              <p className="text-sm font-medium">How are you feeling today?</p>
              <p className="text-xs">Start a conversation or pick one from the sidebar.</p>
            </div>
          )}

          {messages.map((m, i) => (
            <div
              key={i}
              className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}
            >
              <div
                className={`max-w-[70%] p-3 rounded-2xl shadow-lg backdrop-blur-md transition-all duration-300 ${
                  m.role === "user"
                    ? "bg-green-500 text-white rounded-br-sm"
                    : "bg-white/70 text-gray-800 rounded-bl-sm"
                }`}
              >
                {m.content}
                {m.role === "assistant" && (
                  <div className="mt-2 text-right">
                    <button
                      onClick={() => speak(m.content)}
                      className="text-xs text-green-600 hover:underline"
                    >
                      🔊 Speak
                    </button>
                  </div>
                )}
              </div>
            </div>
          ))}

          {isTyping && (
            <div className="text-gray-500 text-sm animate-pulse">Thinking...</div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* INPUT */}
        <div className="p-4 backdrop-blur-lg bg-white/40 border-t border-white/30 flex gap-2">
          <button
            onClick={startMic}
            className={`px-4 rounded-xl text-white transition ${
              listening
                ? "bg-red-500 animate-pulse shadow-lg"
                : "bg-pink-400 hover:scale-105"
            }`}
          >
            {listening ? "🎙️" : "🎤"}
          </button>
          <input
            className="flex-1 p-3 rounded-xl outline-none bg-white/70 backdrop-blur-md focus:ring-2 focus:ring-green-300"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && sendMessage()}
            placeholder="Share what's on your mind..."
          />
          <button
            onClick={sendMessage}
            className="bg-green-500 text-white px-5 rounded-xl hover:scale-105 transition shadow-md"
          >
            Send
          </button>
        </div>
      </div>

      {/* CONFIRMATION MODAL */}
      {showConfirm && (
        <div className="absolute inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-sm">
          <div className="bg-white rounded-2xl shadow-2xl p-6 w-80 space-y-4">
            <h2 className="text-gray-800 font-semibold text-lg">Start a new chat?</h2>
            <p className="text-gray-500 text-sm">
              Your current conversation will be saved in the sidebar. You can return to it anytime.
            </p>
            <div className="flex gap-3 justify-end">
              <button
                onClick={() => setShowConfirm(false)}
                className="px-4 py-2 rounded-xl text-sm text-gray-600 bg-gray-100 hover:bg-gray-200 transition"
              >
                Cancel
              </button>
              <button
                onClick={() => {
                  setShowConfirm(false);
                  createNewSession();
                }}
                className="px-4 py-2 rounded-xl text-sm text-white bg-green-500 hover:bg-green-600 transition"
              >
                Yes, New Chat
              </button>
            </div>
          </div>
        </div>
      )}

    </div>
  );
}