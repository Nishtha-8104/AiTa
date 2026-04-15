import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";

const TOPIC_OPTIONS = [
  { id: "arrays", label: "Arrays & Strings", icon: "⬡", color: "#00d4ff" },
  { id: "linked_lists", label: "Linked Lists", icon: "⬢", color: "#7c3aed" },
  { id: "trees", label: "Trees & Graphs", icon: "⬣", color: "#10b981" },
  { id: "dynamic_programming", label: "Dynamic Programming", icon: "◈", color: "#f59e0b" },
  { id: "sorting", label: "Sorting & Searching", icon: "◆", color: "#ef4444" },
  { id: "recursion", label: "Recursion", icon: "⟳", color: "#8b5cf6" },
  { id: "hashing", label: "Hashing", icon: "◉", color: "#06b6d4" },
  { id: "stacks_queues", label: "Stacks & Queues", icon: "⊞", color: "#f97316" },
  { id: "backtracking", label: "Backtracking", icon: "↩", color: "#84cc16" },
  { id: "bit_manipulation", label: "Bit Manipulation", icon: "⊕", color: "#ec4899" },
  { id: "greedy", label: "Greedy Algorithms", icon: "◎", color: "#14b8a6" },
  { id: "math", label: "Math & Number Theory", icon: "∑", color: "#6366f1" },
];

const LANGUAGE_OPTIONS = ["Python", "JavaScript", "Java", "C++", "C", "Go", "Rust"];
const SKILL_LEVELS = ["Beginner", "Intermediate", "Advanced"];

export default function RegisterPage() {
  const navigate = useNavigate();
  const { register } = useAuth();
  const [step, setStep] = useState(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const [form, setForm] = useState({
    username: "",
    email: "",
    password: "",
    confirmPassword: "",
    full_name: "",
    skill_level: "Beginner",
    preferred_languages: ["Python"],
    interested_topics: [],
  });

  const toggleTopic = (id) => {
    setForm((prev) => ({
      ...prev,
      interested_topics: prev.interested_topics.includes(id)
        ? prev.interested_topics.filter((t) => t !== id)
        : [...prev.interested_topics, id],
    }));
  };

  const toggleLanguage = (lang) => {
    setForm((prev) => ({
      ...prev,
      preferred_languages: prev.preferred_languages.includes(lang)
        ? prev.preferred_languages.filter((l) => l !== lang)
        : [...prev.preferred_languages, lang],
    }));
  };

  const handleStep1 = (e) => {
    e.preventDefault();
    setError("");
    if (form.password !== form.confirmPassword) {
      setError("Passwords do not match");
      return;
    }
    if (form.password.length < 8) {
      setError("Password must be at least 8 characters");
      return;
    }
    setStep(2);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (form.interested_topics.length === 0) {
      setError("Please select at least one topic");
      return;
    }
    setLoading(true);
    setError("");
    try {
      await register({
        username: form.username,
        email: form.email,
        password: form.password,
        full_name: form.full_name,
        skill_level: form.skill_level.toLowerCase(),
        preferred_languages: form.preferred_languages.map((l) => l.toLowerCase()),
        interested_topics: form.interested_topics,
      });
      // Redirect to onboarding for first-time users
      navigate("/onboarding");
    } catch (err) {
      setError(err.response?.data?.detail || "Registration failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={styles.page}>
      {/* Background grid */}
      <div style={styles.grid} />
      <div style={styles.glow1} />
      <div style={styles.glow2} />

      <div style={styles.container}>
        {/* Header */}
        <div style={styles.header}>
          <div style={styles.logo}>
            <span style={styles.logoIcon}>⬡</span>
            <span style={styles.logoText}>ai<span style={styles.logoAccent}>TA</span></span>
          </div>
          <div style={styles.stepRow}>
            {[1, 2].map((s) => (
              <div key={s} style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <div style={{
                  ...styles.stepDot,
                  background: step >= s ? "#00d4ff" : "rgba(255,255,255,0.1)",
                  boxShadow: step >= s ? "0 0 12px #00d4ff80" : "none",
                }} />
                {s < 2 && <div style={styles.stepLine} />}
              </div>
            ))}
          </div>
        </div>

        <div style={styles.card}>
          {step === 1 ? (
            <>
              <h1 style={styles.title}>Create Account</h1>
              <p style={styles.subtitle}>Step 1 of 2 — Your identity</p>

              {error && <div style={styles.errorBox}>{error}</div>}

              <form onSubmit={handleStep1} style={styles.form}>
                <div style={styles.row}>
                  <div style={styles.field}>
                    <label style={styles.label}>Full Name</label>
                    <input
                      style={styles.input}
                      placeholder="Arjun Sharma"
                      value={form.full_name}
                      onChange={(e) => setForm({ ...form, full_name: e.target.value })}
                      required
                    />
                  </div>
                  <div style={styles.field}>
                    <label style={styles.label}>Username</label>
                    <input
                      style={styles.input}
                      placeholder="arjun_dev"
                      value={form.username}
                      onChange={(e) => setForm({ ...form, username: e.target.value })}
                      required
                    />
                  </div>
                </div>

                <div style={styles.field}>
                  <label style={styles.label}>Email</label>
                  <input
                    style={styles.input}
                    type="email"
                    placeholder="arjun@college.edu"
                    value={form.email}
                    onChange={(e) => setForm({ ...form, email: e.target.value })}
                    required
                  />
                </div>

                <div style={styles.row}>
                  <div style={styles.field}>
                    <label style={styles.label}>Password</label>
                    <input
                      style={styles.input}
                      type="password"
                      placeholder="Min 8 characters"
                      value={form.password}
                      onChange={(e) => setForm({ ...form, password: e.target.value })}
                      required
                    />
                  </div>
                  <div style={styles.field}>
                    <label style={styles.label}>Confirm Password</label>
                    <input
                      style={styles.input}
                      type="password"
                      placeholder="Repeat password"
                      value={form.confirmPassword}
                      onChange={(e) => setForm({ ...form, confirmPassword: e.target.value })}
                      required
                    />
                  </div>
                </div>

                <button type="submit" style={styles.btn}>
                  Continue →
                </button>
              </form>
            </>
          ) : (
            <>
              <h1 style={styles.title}>Your Learning Profile</h1>
              <p style={styles.subtitle}>Step 2 of 2 — These topics power every AI agent</p>

              {error && <div style={styles.errorBox}>{error}</div>}

              <form onSubmit={handleSubmit} style={styles.form}>
                {/* Skill Level */}
                <div style={styles.field}>
                  <label style={styles.label}>Current Skill Level</label>
                  <div style={styles.pillRow}>
                    {SKILL_LEVELS.map((level) => (
                      <button
                        key={level}
                        type="button"
                        onClick={() => setForm({ ...form, skill_level: level })}
                        style={{
                          ...styles.pill,
                          background: form.skill_level === level ? "#00d4ff22" : "transparent",
                          border: `1px solid ${form.skill_level === level ? "#00d4ff" : "rgba(255,255,255,0.15)"}`,
                          color: form.skill_level === level ? "#00d4ff" : "rgba(255,255,255,0.6)",
                        }}
                      >
                        {level}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Languages */}
                <div style={styles.field}>
                  <label style={styles.label}>Preferred Languages</label>
                  <div style={styles.pillRow}>
                    {LANGUAGE_OPTIONS.map((lang) => (
                      <button
                        key={lang}
                        type="button"
                        onClick={() => toggleLanguage(lang)}
                        style={{
                          ...styles.pill,
                          background: form.preferred_languages.includes(lang) ? "#7c3aed22" : "transparent",
                          border: `1px solid ${form.preferred_languages.includes(lang) ? "#7c3aed" : "rgba(255,255,255,0.15)"}`,
                          color: form.preferred_languages.includes(lang) ? "#a78bfa" : "rgba(255,255,255,0.6)",
                        }}
                      >
                        {lang}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Topics */}
                <div style={styles.field}>
                  <label style={styles.label}>
                    Topics You Want to Master
                    <span style={{ color: "rgba(255,255,255,0.4)", fontWeight: 400, marginLeft: 8 }}>
                      ({form.interested_topics.length} selected — these are remembered by all agents)
                    </span>
                  </label>
                  <div style={styles.topicGrid}>
                    {TOPIC_OPTIONS.map((topic) => {
                      const selected = form.interested_topics.includes(topic.id);
                      return (
                        <button
                          key={topic.id}
                          type="button"
                          onClick={() => toggleTopic(topic.id)}
                          style={{
                            ...styles.topicCard,
                            background: selected ? `${topic.color}15` : "rgba(255,255,255,0.03)",
                            border: `1px solid ${selected ? topic.color : "rgba(255,255,255,0.08)"}`,
                            boxShadow: selected ? `0 0 16px ${topic.color}30` : "none",
                          }}
                        >
                          <span style={{ fontSize: 20, color: topic.color }}>{topic.icon}</span>
                          <span style={{
                            fontSize: 12,
                            color: selected ? "#fff" : "rgba(255,255,255,0.55)",
                            fontWeight: selected ? 600 : 400,
                          }}>
                            {topic.label}
                          </span>
                          {selected && (
                            <div style={{
                              position: "absolute",
                              top: 6,
                              right: 6,
                              width: 8,
                              height: 8,
                              borderRadius: "50%",
                              background: topic.color,
                              boxShadow: `0 0 6px ${topic.color}`,
                            }} />
                          )}
                        </button>
                      );
                    })}
                  </div>
                </div>

                <div style={styles.btnRow}>
                  <button
                    type="button"
                    onClick={() => setStep(1)}
                    style={styles.btnGhost}
                  >
                    ← Back
                  </button>
                  <button type="submit" style={styles.btn} disabled={loading}>
                    {loading ? "Creating account..." : "Start Learning →"}
                  </button>
                </div>
              </form>
            </>
          )}

          <p style={styles.loginLink}>
            Already have an account?{" "}
            <Link to="/login" style={{ color: "#00d4ff", textDecoration: "none" }}>
              Sign in
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}

const styles = {
  page: {
    minHeight: "100vh",
    background: "#050810",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    padding: "40px 20px",
    fontFamily: "'DM Sans', 'Segoe UI', sans-serif",
    position: "relative",
    overflow: "hidden",
  },
  grid: {
    position: "fixed",
    inset: 0,
    backgroundImage: `
      linear-gradient(rgba(0,212,255,0.03) 1px, transparent 1px),
      linear-gradient(90deg, rgba(0,212,255,0.03) 1px, transparent 1px)
    `,
    backgroundSize: "48px 48px",
    pointerEvents: "none",
  },
  glow1: {
    position: "fixed",
    top: "-20%",
    right: "-10%",
    width: 600,
    height: 600,
    borderRadius: "50%",
    background: "radial-gradient(circle, rgba(0,212,255,0.08) 0%, transparent 70%)",
    pointerEvents: "none",
  },
  glow2: {
    position: "fixed",
    bottom: "-20%",
    left: "-10%",
    width: 500,
    height: 500,
    borderRadius: "50%",
    background: "radial-gradient(circle, rgba(124,58,237,0.08) 0%, transparent 70%)",
    pointerEvents: "none",
  },
  container: {
    width: "100%",
    maxWidth: 640,
    position: "relative",
    zIndex: 1,
  },
  header: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    marginBottom: 32,
  },
  logo: {
    display: "flex",
    alignItems: "center",
    gap: 10,
  },
  logoIcon: {
    fontSize: 24,
    color: "#00d4ff",
    filter: "drop-shadow(0 0 8px #00d4ff80)",
  },
  logoText: {
    fontSize: 22,
    fontWeight: 700,
    color: "#fff",
    letterSpacing: "-0.5px",
  },
  logoAccent: {
    color: "#00d4ff",
  },
  stepRow: {
    display: "flex",
    alignItems: "center",
    gap: 4,
  },
  stepDot: {
    width: 10,
    height: 10,
    borderRadius: "50%",
    transition: "all 0.3s",
  },
  stepLine: {
    width: 28,
    height: 1,
    background: "rgba(255,255,255,0.15)",
  },
  card: {
    background: "rgba(255,255,255,0.03)",
    border: "1px solid rgba(255,255,255,0.08)",
    borderRadius: 20,
    padding: "40px",
    backdropFilter: "blur(20px)",
  },
  title: {
    fontSize: 28,
    fontWeight: 700,
    color: "#fff",
    margin: "0 0 6px",
    letterSpacing: "-0.5px",
  },
  subtitle: {
    fontSize: 14,
    color: "rgba(255,255,255,0.4)",
    margin: "0 0 32px",
  },
  errorBox: {
    background: "rgba(239,68,68,0.1)",
    border: "1px solid rgba(239,68,68,0.3)",
    borderRadius: 10,
    padding: "12px 16px",
    color: "#fca5a5",
    fontSize: 14,
    marginBottom: 20,
  },
  form: {
    display: "flex",
    flexDirection: "column",
    gap: 20,
  },
  row: {
    display: "grid",
    gridTemplateColumns: "1fr 1fr",
    gap: 16,
  },
  field: {
    display: "flex",
    flexDirection: "column",
    gap: 8,
  },
  label: {
    fontSize: 13,
    fontWeight: 500,
    color: "rgba(255,255,255,0.6)",
    letterSpacing: "0.3px",
  },
  input: {
    background: "rgba(255,255,255,0.05)",
    border: "1px solid rgba(255,255,255,0.1)",
    borderRadius: 10,
    padding: "12px 16px",
    color: "#fff",
    fontSize: 14,
    outline: "none",
    transition: "border-color 0.2s",
  },
  pillRow: {
    display: "flex",
    flexWrap: "wrap",
    gap: 8,
  },
  pill: {
    padding: "8px 16px",
    borderRadius: 20,
    fontSize: 13,
    fontWeight: 500,
    cursor: "pointer",
    transition: "all 0.2s",
  },
  topicGrid: {
    display: "grid",
    gridTemplateColumns: "repeat(3, 1fr)",
    gap: 10,
    marginTop: 4,
  },
  topicCard: {
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    gap: 8,
    padding: "14px 10px",
    borderRadius: 12,
    cursor: "pointer",
    transition: "all 0.2s",
    position: "relative",
    textAlign: "center",
  },
  btn: {
    background: "linear-gradient(135deg, #00d4ff, #0099cc)",
    border: "none",
    borderRadius: 12,
    padding: "14px 28px",
    color: "#000",
    fontSize: 15,
    fontWeight: 700,
    cursor: "pointer",
    letterSpacing: "0.3px",
    transition: "opacity 0.2s",
  },
  btnGhost: {
    background: "transparent",
    border: "1px solid rgba(255,255,255,0.15)",
    borderRadius: 12,
    padding: "14px 24px",
    color: "rgba(255,255,255,0.6)",
    fontSize: 14,
    cursor: "pointer",
  },
  btnRow: {
    display: "flex",
    gap: 12,
    justifyContent: "space-between",
  },
  loginLink: {
    textAlign: "center",
    fontSize: 14,
    color: "rgba(255,255,255,0.4)",
    marginTop: 24,
    marginBottom: 0,
  },
};