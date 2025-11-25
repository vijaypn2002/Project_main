// src/components/SearchBar.jsx
import { useEffect, useRef, useState, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import api from "../lib/api";

/**
 * Accessible search with suggestions (combobox pattern)
 * - Debounced fetching
 * - Arrow key navigation + Enter
 * - Esc to close
 * - Click-outside to close
 */
export default function SearchBar() {
  const nav = useNavigate();

  const [q, setQ] = useState("");
  const [open, setOpen] = useState(false);
  const [suggestions, setSuggestions] = useState([]);
  const [highlight, setHighlight] = useState(-1); // index in suggestions
  const [loading, setLoading] = useState(false);

  const rootRef = useRef(null);
  const inputRef = useRef(null);
  const abortRef = useRef(null);
  const debounceRef = useRef(null);

  const listboxId = useMemo(() => "search-suggest-" + Math.random().toString(36).slice(2), []);

  // --- helpers ---
  function submit(term) {
    const value = (term ?? q).trim();
    if (!value) return;
    nav(`/search?q=${encodeURIComponent(value)}`);
    setOpen(false);
    setHighlight(-1);
  }

  function clear() {
    setQ("");
    setSuggestions([]);
    setHighlight(-1);
    setOpen(false);
    inputRef.current?.focus();
  }

  // --- fetch suggestions with debounce + cancel ---
  async function fetchSuggest(term) {
    if (abortRef.current) {
      abortRef.current.abort();
      abortRef.current = null;
    }
    if (!term || term.length < 2) {
      setSuggestions([]);
      setLoading(false);
      return;
    }

    const controller = new AbortController();
    abortRef.current = controller;

    try {
      setLoading(true);
      const r = await api.get("/search/suggest", {
        params: { q: term, _public: 1 },
        signal: controller.signal,
      });
      setSuggestions(r?.data?.suggestions || []);
    } catch {
      if (!controller.signal.aborted) setSuggestions([]);
    } finally {
      if (!controller.signal.aborted) setLoading(false);
    }
  }

  function debouncedFetch(term) {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => fetchSuggest(term), 180);
  }

  // --- click outside to close ---
  useEffect(() => {
    function onDocClick(e) {
      if (!rootRef.current?.contains(e.target)) {
        setOpen(false);
        setHighlight(-1);
      }
    }
    document.addEventListener("mousedown", onDocClick);
    return () => document.removeEventListener("mousedown", onDocClick);
  }, []);

  // --- keyboard handlers ---
  function onKeyDown(e) {
    if (!open && (e.key === "ArrowDown" || e.key === "ArrowUp")) {
      setOpen(true);
      return;
    }
    switch (e.key) {
      case "ArrowDown":
        e.preventDefault();
        setHighlight((h) => {
          const next = Math.min((h < 0 ? -1 : h) + 1, suggestions.length - 1);
          return next;
        });
        break;
      case "ArrowUp":
        e.preventDefault();
        setHighlight((h) => Math.max(h - 1, -1));
        break;
      case "Enter":
        if (highlight >= 0 && suggestions[highlight]) {
          e.preventDefault();
          submit(suggestions[highlight]);
        }
        break;
      case "Escape":
        if (open) {
          e.preventDefault();
          setOpen(false);
          setHighlight(-1);
        }
        break;
      default:
        break;
    }
  }

  const activeDescendant =
    highlight >= 0 && open ? `${listboxId}-opt-${highlight}` : undefined;

  return (
    <div className="relative w-full max-w-xl" ref={rootRef}>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          submit();
        }}
        className="flex items-center bg-gray-100 rounded-md overflow-hidden focus-within:ring-2 ring-blue-500"
        role="search"
        aria-label="Site search"
      >
        <input
          ref={inputRef}
          type="search"
          className="w-full md:w-[520px] px-4 py-2 bg-transparent outline-none"
          placeholder="Search for products, brands and more"
          value={q}
          onChange={(e) => {
            const v = e.target.value;
            setQ(v);
            setOpen(!!v);
            setHighlight(-1);
            debouncedFetch(v);
          }}
          onFocus={() => {
            if (q) {
              setOpen(true);
              debouncedFetch(q);
            }
          }}
          onKeyDown={onKeyDown}
          role="combobox"
          aria-expanded={open}
          aria-controls={listboxId}
          aria-autocomplete="list"
          aria-activedescendant={activeDescendant}
        />

        {q ? (
          <button
            type="button"
            onClick={clear}
            className="px-2 text-gray-500 hover:text-gray-700"
            aria-label="Clear search"
            title="Clear"
          >
            ✕
          </button>
        ) : null}

        <button
          className="px-4 py-2 bg-blue-600 text-white hover:bg-blue-700"
          type="submit"
          aria-label="Search"
        >
          Search
        </button>
      </form>

      {open && (
        <div
          id={listboxId}
          role="listbox"
          className="absolute mt-1 w-full bg-white border rounded shadow-lg max-h-72 overflow-auto z-50"
        >
          {loading && (
            <div className="px-4 py-2 text-sm text-gray-500">Searching…</div>
          )}

          {!loading && suggestions.length === 0 && q.length >= 2 && (
            <div className="px-4 py-2 text-sm text-gray-500">No suggestions</div>
          )}

          {!loading &&
            suggestions.map((s, i) => {
              const active = i === highlight;
              return (
                <button
                  key={`${s}-${i}`}
                  id={`${listboxId}-opt-${i}`}
                  role="option"
                  aria-selected={active}
                  className={[
                    "w-full text-left px-4 py-2",
                    active ? "bg-blue-50" : "hover:bg-gray-50",
                  ].join(" ")}
                  onMouseEnter={() => setHighlight(i)}
                  onMouseDown={(e) => {
                    e.preventDefault(); // keep focus to avoid blur
                    submit(s);
                  }}
                >
                  {s}
                </button>
              );
            })}
        </div>
      )}
    </div>
  );
}
