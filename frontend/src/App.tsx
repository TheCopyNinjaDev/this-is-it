import { useEffect, useMemo, useRef, useState } from "react";

type TelegramWebApp = {
  BackButton?: {
    show: () => void;
    hide: () => void;
    onClick: (callback: () => void) => void;
    offClick: (callback: () => void) => void;
  };
  HapticFeedback?: {
    impactOccurred: (style: "light" | "medium" | "heavy" | "rigid" | "soft") => void;
    notificationOccurred: (type: "error" | "success" | "warning") => void;
  };
  initData: string;
  initDataUnsafe?: {
    start_param?: string;
    user?: {
      id?: number;
    };
  };
  ready: () => void;
  expand: () => void;
  openTelegramLink?: (url: string) => void;
  openLink?: (url: string, options?: { try_instant_view?: boolean }) => void;
  close?: () => void;
  requestFullscreen?: () => void;
  disableVerticalSwipes?: () => void;
};

type Participant = {
  user_id: number;
  name: string;
  is_creator: boolean;
};

type Idea = {
  id: number;
  title: string;
  description: string;
  category: string;
  vibe: string;
};

type Room = {
  id: string;
  status: string;
  created_at: string;
  updated_at: string;
  matched_at: string | null;
  match_revealed_at: string | null;
  participants: Participant[];
  participants_count: number;
  max_participants: number;
  can_start: boolean;
  invite_url: string;
  photo_upload_url: string | null;
  photo_uploaded: boolean;
  postcard_url: string | null;
  memories: RoomMemory[];
  matched_idea: Idea | null;
};

type RoomMemory = {
  id: number;
  uploaded_by_user_id: number;
  uploaded_by_name: string;
  created_at: string;
  matched_at: string | null;
  photo_url: string | null;
  postcard_url: string | null;
};

type RoomCollection = {
  active: Room[];
  completed: Room[];
};

type SwipeState = {
  room_status: string;
  matched: boolean;
  matched_idea: Idea | null;
  next_idea: Idea | null;
};

type SwipeCardProps = {
  busy: boolean;
  idea: Idea;
  onSwipe: (liked: boolean) => void;
};

type ScratchRevealProps = {
  idea: Idea;
  initiallyRevealed: boolean;
  onReveal: () => void;
};

type HomeRoomCardProps = {
  room: Room;
  title: string;
  subtitle: string;
  onOpen: (roomId: string) => void;
};

type MemoryPreviewProps = {
  memory: RoomMemory;
  onOpen: (memory: RoomMemory) => void;
};

type GalleryMemory = RoomMemory & {
  room_id: string;
  idea_title: string;
};

type GalleryOwnerFilter = "all" | "mine" | "partner";
type GallerySort = "newest" | "oldest";

declare global {
  interface Window {
    Telegram?: {
      WebApp?: TelegramWebApp;
    };
  }
}

const apiBaseUrl = (import.meta.env.VITE_API_BASE_URL ?? "/api").replace(/\/$/, "");

async function api<T>(path: string, token: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${apiBaseUrl}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
      ...(init?.headers ?? {}),
    },
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `HTTP ${response.status}`);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}

function IconHeart() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M12 20.4 4.9 13.9a4.8 4.8 0 0 1 6.8-6.8l.3.3.3-.3a4.8 4.8 0 1 1 6.8 6.8L12 20.4Z" fill="currentColor" />
    </svg>
  );
}

function IconSpark() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="m12 2 1.8 5.2L19 9l-5.2 1.8L12 16l-1.8-5.2L5 9l5.2-1.8L12 2Zm7 13 .8 2.2L22 18l-2.2.8L19 21l-.8-2.2L16 18l2.2-.8L19 15ZM5 14l1.1 3L9 18l-2.9 1L5 22l-1.1-3L1 18l2.9-1L5 14Z" fill="currentColor" />
    </svg>
  );
}

function IconShare() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M18 8a3 3 0 1 0-2.8-4H15a3 3 0 0 0 .2 1L8.7 8.3a3 3 0 0 0-1.7-.5 3 3 0 1 0 1.7 5.5l6.6 3.3A3 3 0 1 0 16 15a3 3 0 0 0-.2 1l-6.6-3.3a3 3 0 0 0 0-1.4L15.8 8a3 3 0 0 0 2.2 1Z" fill="currentColor" />
    </svg>
  );
}

function IconUsers() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M9 11a3.5 3.5 0 1 0-3.5-3.5A3.5 3.5 0 0 0 9 11Zm6 1a3 3 0 1 0-3-3 3 3 0 0 0 3 3ZM9 13c-3.3 0-6 2-6 4.5V20h12v-2.5C15 15 12.3 13 9 13Zm6 1c-.7 0-1.4.1-2 .4 1.4 1 2.3 2.4 2.3 4V20H21v-1.5c0-2.5-2.7-4.5-6-4.5Z" fill="currentColor" />
    </svg>
  );
}

function IconIdea() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M12 3a6.5 6.5 0 0 0-3.9 11.8c.8.6 1.4 1.3 1.7 2.2h4.4c.3-.9.9-1.6 1.7-2.2A6.5 6.5 0 0 0 12 3Zm-2 16h4v1a2 2 0 0 1-4 0v-1Z" fill="currentColor" />
    </svg>
  );
}

function IconGallery() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M5 4h14a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2Zm0 2v8.4l3.2-3.2a1.5 1.5 0 0 1 2.1 0l2.1 2.1 3.8-3.8a1.5 1.5 0 0 1 2.1 0L21 12.2V6H5Zm0 12h14v-3l-3.9-3.9-3.8 3.8a1.5 1.5 0 0 1-2.1 0L9.3 13 5 17.3V18Zm4-8.8A1.8 1.8 0 1 0 9 5.6a1.8 1.8 0 0 0 0 3.6Z" fill="currentColor" />
    </svg>
  );
}

function statusLabel(status: string): string {
  if (status === "waiting") {
    return "Ожидание";
  }
  if (status === "active") {
    return "В процессе";
  }
  if (status === "matched") {
    return "Завершена";
  }
  return status;
}

function formatMatchDate(value: string): string {
  const date = new Date(value);
  return new Intl.DateTimeFormat("ru-RU", {
    day: "numeric",
    month: "long",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

function ScratchReveal({ idea, initiallyRevealed, onReveal }: ScratchRevealProps) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const [revealed, setRevealed] = useState(initiallyRevealed);
  const [dragging, setDragging] = useState(false);
  const checkCounterRef = useRef(0);
  const scratchPointsRef = useRef(0);

  useEffect(() => {
    setRevealed(initiallyRevealed);
  }, [idea.id, initiallyRevealed]);

  useEffect(() => {
    if (initiallyRevealed) {
      return;
    }

    const canvas = canvasRef.current;
    if (!canvas) {
      return;
    }

    const context = canvas.getContext("2d");
    if (!context) {
      return;
    }

    const ratio = window.devicePixelRatio || 1;
    const width = canvas.clientWidth;
    const height = canvas.clientHeight;
    canvas.width = width * ratio;
    canvas.height = height * ratio;
    context.scale(ratio, ratio);

    const gradient = context.createLinearGradient(0, 0, width, height);
    gradient.addColorStop(0, "#f0d7de");
    gradient.addColorStop(0.5, "#dbc8ef");
    gradient.addColorStop(1, "#f7e4be");
    context.fillStyle = gradient;
    context.fillRect(0, 0, width, height);

    context.fillStyle = "rgba(255,255,255,0.22)";
    for (let index = 0; index < 28; index += 1) {
      context.beginPath();
      context.arc(Math.random() * width, Math.random() * height, 8 + Math.random() * 22, 0, Math.PI * 2);
      context.fill();
    }

    context.fillStyle = "#5d4867";
    context.font = "600 18px 'Avenir Next', 'Trebuchet MS', sans-serif";
    context.textAlign = "center";
    context.fillText("Сотри, чтобы открыть", width / 2, height / 2 - 8);
    context.font = "400 13px 'Avenir Next', 'Trebuchet MS', sans-serif";
    context.fillText("Здесь спрятана ваша идея для свидания", width / 2, height / 2 + 18);
  }, [idea.id, initiallyRevealed]);

  function scratch(clientX: number, clientY: number) {
    const canvas = canvasRef.current;
    if (!canvas || revealed) {
      return;
    }

    const context = canvas.getContext("2d");
    if (!context) {
      return;
    }

    const bounds = canvas.getBoundingClientRect();
    const x = clientX - bounds.left;
    const y = clientY - bounds.top;

    context.save();
    context.globalCompositeOperation = "destination-out";
    context.beginPath();
    context.arc(x, y, 24, 0, Math.PI * 2);
    context.fill();
    context.restore();

    scratchPointsRef.current += 1;
    checkCounterRef.current += 1;
    if (checkCounterRef.current < 6) {
      return;
    }
    checkCounterRef.current = 0;

    const image = context.getImageData(0, 0, canvas.width, canvas.height);
    let transparent = 0;
    let samples = 0;
    const step = 10;
    for (let yIndex = 0; yIndex < canvas.height; yIndex += step) {
      for (let xIndex = 0; xIndex < canvas.width; xIndex += step) {
        const alphaIndex = (yIndex * canvas.width + xIndex) * 4 + 3;
        samples += 1;
        if (image.data[alphaIndex] < 24) {
          transparent += 1;
        }
      }
    }

    if (scratchPointsRef.current >= 28 && samples > 0 && transparent / samples >= 0.82) {
      setRevealed(true);
      onReveal();
    }
  }

  return (
    <section className="match-stage">
      <div className="match-stage__glow" />
      <div className="match-stage__ticket">
        <div className="match-stage__stamp">
          <IconHeart />
          <span>Это мэтч</span>
        </div>
        <div className="match-stage__content">
          <p className="eyebrow">Идея открыта</p>
          <h1>{idea.title}</h1>
          <p>{idea.description}</p>
          <div className="meta-pill meta-pill--match">
            <span>{idea.category}</span>
            <span>{idea.vibe}</span>
          </div>
        </div>
        {!revealed ? (
          <canvas
            ref={canvasRef}
            className={`scratch-layer${dragging ? " scratch-layer--dragging" : ""}`}
            onPointerDown={(event) => {
              setDragging(true);
              scratch(event.clientX, event.clientY);
            }}
            onPointerMove={(event) => {
              if (!dragging) {
                return;
              }
              scratch(event.clientX, event.clientY);
            }}
            onPointerUp={() => setDragging(false)}
            onPointerLeave={() => setDragging(false)}
          />
        ) : null}
      </div>
    </section>
  );
}

function MemoryPreview({ memory, onOpen }: MemoryPreviewProps) {
  if (!memory.postcard_url) {
    return null;
  }

  return (
    <button className="memory-preview" onClick={() => onOpen(memory)}>
      <img className="memory-preview__image" src={memory.postcard_url} alt={`Открытка от ${memory.uploaded_by_name}`} />
      <div className="memory-preview__overlay">
        <strong>{memory.uploaded_by_name}</strong>
        <span>{formatMatchDate(memory.created_at)}</span>
      </div>
    </button>
  );
}

function MatchBurst() {
  return (
    <div className="match-burst" aria-hidden="true">
      <span className="match-burst__piece match-burst__piece--1">✨</span>
      <span className="match-burst__piece match-burst__piece--2">💖</span>
      <span className="match-burst__piece match-burst__piece--3">✨</span>
      <span className="match-burst__piece match-burst__piece--4">💘</span>
      <span className="match-burst__piece match-burst__piece--5">✨</span>
      <span className="match-burst__piece match-burst__piece--6">💞</span>
    </div>
  );
}

function SwipeCard({ busy, idea, onSwipe }: SwipeCardProps) {
  const [offsetX, setOffsetX] = useState(0);
  const [dragging, setDragging] = useState(false);
  const [isAnimatingOut, setIsAnimatingOut] = useState(false);
  const startXRef = useRef(0);

  useEffect(() => {
    setOffsetX(0);
    setDragging(false);
    setIsAnimatingOut(false);
  }, [idea.id]);

  function endSwipe(forceDecision?: boolean) {
    const threshold = 118;
    const decision =
      typeof forceDecision === "boolean" ? forceDecision : Math.abs(offsetX) >= threshold ? offsetX > 0 : null;

    if (decision === null) {
      setDragging(false);
      setOffsetX(0);
      return;
    }

    setDragging(false);
    setIsAnimatingOut(true);
    setOffsetX(decision ? 420 : -420);
    window.setTimeout(() => {
      onSwipe(decision);
    }, 190);
  }

  const tilt = Math.max(-16, Math.min(16, offsetX / 15));
  const overlayLabel = offsetX > 36 ? "Точно да" : offsetX < -36 ? "Нет" : "";

  function beginDrag(clientX: number) {
    if (busy) {
      return;
    }
    startXRef.current = clientX - offsetX;
    setDragging(true);
  }

  function moveDrag(clientX: number) {
    if (!dragging || busy) {
      return;
    }
    setOffsetX(clientX - startXRef.current);
  }

  return (
    <section className="swipe-stage">
      <div
        className={`swipe-card${dragging ? " swipe-card--dragging" : ""}${isAnimatingOut ? " swipe-card--flying" : ""}`}
        style={{ transform: `translateX(${offsetX}px) rotate(${tilt}deg)` }}
        onPointerDown={(event) => {
          beginDrag(event.clientX);
        }}
        onPointerMove={(event) => {
          moveDrag(event.clientX);
        }}
        onPointerUp={() => endSwipe()}
        onPointerCancel={() => endSwipe()}
        onPointerLeave={() => {
          if (dragging) {
            endSwipe();
          }
        }}
        onTouchStart={(event) => {
          const touch = event.touches[0];
          if (touch) {
            beginDrag(touch.clientX);
          }
        }}
        onTouchMove={(event) => {
          const touch = event.touches[0];
          if (touch) {
            moveDrag(touch.clientX);
          }
        }}
        onTouchEnd={() => endSwipe()}
      >
        <div className="swipe-card__float float-orb float-orb--one" />
        <div className="swipe-card__float float-orb float-orb--two" />
        <div className="swipe-card__topline">
          <div className="meta-pill">
            <span>{idea.category}</span>
            <span>{idea.vibe}</span>
          </div>
          <div className={`swipe-card__signal ${offsetX > 0 ? "swipe-card__signal--like" : offsetX < 0 ? "swipe-card__signal--dislike" : ""}`}>
            {overlayLabel}
          </div>
        </div>
        <div className="swipe-card__illustration">
          <div className="moon-mark">
            <IconSpark />
          </div>
        </div>
        <div className="swipe-card__text">
          <h1>{idea.title}</h1>
          <p>{idea.description}</p>
        </div>
        <div className="swipe-card__canvas">
          <div className="swipe-card__canvas-blur swipe-card__canvas-blur--left" />
          <div className="swipe-card__canvas-blur swipe-card__canvas-blur--right" />
          <div className="swipe-card__canvas-panel">
            <div className="swipe-card__canvas-copy">
              <span className="swipe-card__canvas-tag">Откликается?</span>
              <strong>{idea.vibe}</strong>
              <p>Если эта идея feels right, отправь её вправо. Если не твоя энергия, отпусти влево.</p>
            </div>
          </div>
        </div>
      </div>
      <div className="actions actions--floating">
        <button className="action action--ghost" disabled={busy} onClick={() => endSwipe(false)}>
          <span className="action__icon">💔</span>
          <span>Нет</span>
        </button>
        <button className="action action--fire" disabled={busy} onClick={() => endSwipe(true)}>
          <span className="action__icon">❤️‍🔥</span>
          <span>Да</span>
        </button>
      </div>
    </section>
  );
}

function HomeRoomCard({ room, title, subtitle, onOpen }: HomeRoomCardProps) {
  return (
    <button className="room-card" onClick={() => onOpen(room.id)}>
      <div className="room-card__head">
        <div>
          <strong>{title}</strong>
          <p>{subtitle}</p>
        </div>
        <span className={`room-badge room-badge--${room.status}`}>{statusLabel(room.status)}</span>
      </div>
      <div className="room-card__meta">
        <span>{room.participants_count}/{room.max_participants} участника</span>
        <span>
          {room.participants.map((participant) => participant.name).join(", ") || "Пока пусто"}
        </span>
      </div>
      <span className="room-card__cta">{room.status === "matched" ? "Посмотреть мэтч" : "Открыть комнату"}</span>
    </button>
  );
}

function App() {
  const webApp = window.Telegram?.WebApp;
  const currentTelegramUserId = webApp?.initDataUnsafe?.user?.id ?? null;
  const initialRoomId = useMemo(() => {
    const params = new URLSearchParams(window.location.search);
    const queryRoomId = params.get("room_id");
    if (queryRoomId) {
      return queryRoomId;
    }

    const startAppParam = params.get("tgWebAppStartParam") ?? params.get("startapp");
    if (startAppParam) {
      return startAppParam;
    }

    const startParam = webApp?.initDataUnsafe?.start_param;
    if (startParam) {
      return startParam;
    }

    return "";
  }, [webApp?.initDataUnsafe?.start_param]);
  const [roomId, setRoomId] = useState(initialRoomId);
  const [token, setToken] = useState("");
  const [room, setRoom] = useState<Room | null>(null);
  const [rooms, setRooms] = useState<RoomCollection | null>(null);
  const [swipeState, setSwipeState] = useState<SwipeState | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [socketVersion, setSocketVersion] = useState(0);
  const [showMatchBurst, setShowMatchBurst] = useState(false);
  const [matchRevealed, setMatchRevealed] = useState(false);
  const [openedMemory, setOpenedMemory] = useState<RoomMemory | null>(null);
  const [galleryOpen, setGalleryOpen] = useState(false);
  const [galleryOwnerFilter, setGalleryOwnerFilter] = useState<GalleryOwnerFilter>("all");
  const [galleryIdeaFilter, setGalleryIdeaFilter] = useState("all");
  const [gallerySort, setGallerySort] = useState<GallerySort>("newest");
  const celebratedMatchRef = useRef<string | null>(null);

  const globalGalleryMemories = useMemo<GalleryMemory[]>(() => {
    if (!rooms?.completed?.length) {
      return [];
    }

    return rooms.completed.flatMap((completedRoom) =>
      completedRoom.memories
        .filter((memory) => memory.photo_url)
        .map((memory) => ({
          ...memory,
          room_id: completedRoom.id,
          idea_title: completedRoom.matched_idea?.title ?? "Идея для свидания",
        })),
    );
  }, [rooms]);

  const galleryIdeaOptions = useMemo(() => {
    return Array.from(new Set(globalGalleryMemories.map((memory) => memory.idea_title))).sort((left, right) =>
      left.localeCompare(right, "ru"),
    );
  }, [globalGalleryMemories]);

  const filteredGalleryMemories = useMemo(() => {
    const filtered = globalGalleryMemories.filter((memory) => {
      if (galleryOwnerFilter === "mine" && memory.uploaded_by_user_id !== currentTelegramUserId) {
        return false;
      }
      if (galleryOwnerFilter === "partner" && memory.uploaded_by_user_id === currentTelegramUserId) {
        return false;
      }
      if (galleryIdeaFilter !== "all" && memory.idea_title !== galleryIdeaFilter) {
        return false;
      }
      return true;
    });

    filtered.sort((left, right) => {
      const leftTime = new Date(left.created_at).getTime();
      const rightTime = new Date(right.created_at).getTime();
      return gallerySort === "newest" ? rightTime - leftTime : leftTime - rightTime;
    });
    return filtered;
  }, [currentTelegramUserId, galleryIdeaFilter, galleryOwnerFilter, gallerySort, globalGalleryMemories]);

  useEffect(() => {
    webApp?.ready();
    webApp?.expand();
    webApp?.requestFullscreen?.();
    webApp?.disableVerticalSwipes?.();

    const initData = webApp?.initData;
    if (!initData) {
      setError("Открой этот экран внутри Telegram WebApp, чтобы войти.");
      setLoading(false);
      return;
    }

    void (async () => {
      try {
        const auth = await fetch(`${apiBaseUrl}/auth/telegram`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ init_data: initData }),
        });
        if (!auth.ok) {
          throw new Error("Не удалось пройти авторизацию Telegram");
        }

        const data = (await auth.json()) as { access_token: string };
        setToken(data.access_token);
      } catch (requestError) {
        setError(requestError instanceof Error ? requestError.message : "Ошибка авторизации");
        setLoading(false);
      }
    })();
  }, [webApp]);

  function playMatchSound() {
    const AudioCtx =
      window.AudioContext ||
      (window as Window & { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
    if (!AudioCtx) {
      return;
    }

    const audio = new AudioCtx();
    const now = audio.currentTime;
    const notes = [659.25, 783.99, 987.77];
    notes.forEach((frequency, index) => {
      const oscillator = audio.createOscillator();
      const gain = audio.createGain();
      oscillator.type = "triangle";
      oscillator.frequency.value = frequency;
      gain.gain.setValueAtTime(0.0001, now);
      gain.gain.exponentialRampToValueAtTime(0.08, now + 0.04 + index * 0.05);
      gain.gain.exponentialRampToValueAtTime(0.0001, now + 0.24 + index * 0.06);
      oscillator.connect(gain);
      gain.connect(audio.destination);
      oscillator.start(now + index * 0.06);
      oscillator.stop(now + 0.34 + index * 0.06);
    });

    window.setTimeout(() => {
      void audio.close();
    }, 700);
  }

  function replaceRoomInUrl(nextRoomId: string) {
    const url = new URL(window.location.href);
    if (nextRoomId) {
      url.searchParams.set("room_id", nextRoomId);
    } else {
      url.searchParams.delete("room_id");
    }
    window.history.replaceState({}, "", `${url.pathname}${url.search}`);
  }

  function openRoom(nextRoomId: string) {
    replaceRoomInUrl(nextRoomId);
    setRoomId(nextRoomId);
    setRoom(null);
    setSwipeState(null);
    setError("");
  }

  async function leaveRoom(nextRoomId = "") {
    if (!token || !roomId || room?.status === "matched") {
      return;
    }

    try {
      await api<void>(`/rooms/${roomId}/leave`, token, {
        method: "POST",
        body: JSON.stringify({}),
      });
    } catch {
      // Best effort cleanup on navigation away from the room.
    } finally {
      if (nextRoomId !== roomId) {
        setRoom(null);
        setSwipeState(null);
      }
    }
  }

  async function goHome() {
    await leaveRoom();
    replaceRoomInUrl("");
    setRoomId("");
    setRoom(null);
    setSwipeState(null);
    setError("");
    if (token) {
      try {
        await loadRooms(token);
      } catch {
        // Keep the existing screen state if refresh fails.
      }
    }
  }

  useEffect(() => {
    const backButton = webApp?.BackButton;
    if (!backButton) {
      return;
    }

    const handleBack = () => {
      if (openedMemory) {
        setOpenedMemory(null);
        return;
      }
      if (galleryOpen) {
        setGalleryOpen(false);
        return;
      }
      void goHome();
    };

    if (roomId || galleryOpen || openedMemory) {
      backButton.show();
      backButton.onClick(handleBack);
    } else {
      backButton.hide();
    }

    return () => {
      backButton.offClick(handleBack);
      if (!roomId && !galleryOpen && !openedMemory) {
        backButton.hide();
      }
    };
  }, [galleryOpen, openedMemory, roomId, webApp, token, room?.status]);

  async function loadRooms(tokenValue: string) {
    const list = await api<RoomCollection>("/rooms/mine", tokenValue);
    setRooms(list);
  }

  useEffect(() => {
    if (!token) {
      return;
    }

    void (async () => {
      try {
        setLoading(true);

        if (!roomId) {
          setRoom(null);
          setSwipeState(null);
          await loadRooms(token);
          setError("");
          return;
        }

        const joinedRoom = await api<Room>(`/rooms/${roomId}/join`, token, {
          method: "POST",
          body: JSON.stringify({}),
        });
        setRoom(joinedRoom);
        setRooms(null);

        if (joinedRoom.status !== "waiting") {
          const next = await api<SwipeState>(`/rooms/${roomId}/ideas/next`, token);
          setSwipeState(next);
        } else {
          setSwipeState(null);
        }

        setError("");
      } catch (requestError) {
        setError(requestError instanceof Error ? requestError.message : "Не удалось загрузить комнату");
      } finally {
        setLoading(false);
      }
    })();
  }, [roomId, token]);

  useEffect(() => {
    if (!token || !roomId) {
      return;
    }

    const handlePageHide = () => {
      if (room?.status === "matched") {
        return;
      }

      void fetch(`${apiBaseUrl}/rooms/${roomId}/leave`, {
        method: "POST",
        keepalive: true,
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({}),
      });
    };

    window.addEventListener("pagehide", handlePageHide);
    return () => {
      window.removeEventListener("pagehide", handlePageHide);
    };
  }, [room?.status, roomId, token]);

  async function refreshRoom() {
    if (!token || !roomId) {
      return;
    }

    const nextRoom = await api<Room>(`/rooms/${roomId}`, token);
    setRoom(nextRoom);

    if (nextRoom.status !== "waiting") {
      const next = await api<SwipeState>(`/rooms/${roomId}/ideas/next`, token);
      setSwipeState(next);
    } else {
      setSwipeState(null);
    }
  }

  async function createRoom() {
    if (!token) {
      return;
    }

    setBusy(true);
    try {
      const createdRoom = await api<Room>("/rooms", token, {
        method: "POST",
        body: JSON.stringify({}),
      });
      openRoom(createdRoom.id);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Не удалось создать комнату");
    } finally {
      setBusy(false);
    }
  }

  function shareInviteLink() {
    if (!room?.invite_url) {
      return;
    }

    const shareText = encodeURIComponent("Пойдём выберем идею для свидания");
    const shareUrl = encodeURIComponent(room.invite_url);
    const telegramShareUrl = `https://t.me/share/url?url=${shareUrl}&text=${shareText}`;

    if (webApp?.openTelegramLink) {
      webApp.openTelegramLink(telegramShareUrl);
      return;
    }

    if (webApp?.openLink) {
      webApp.openLink(telegramShareUrl, { try_instant_view: false });
      return;
    }

    window.open(telegramShareUrl, "_blank", "noopener,noreferrer");
  }

  function openPhotoUploadFlow() {
    if (!room?.photo_upload_url) {
      return;
    }

    window.alert("Сейчас откроется чат с ботом. Любой из вас может отправить туда несколько фото свидания, и бот соберёт открытки автоматически.");
    if (webApp?.openTelegramLink) {
      webApp.openTelegramLink(room.photo_upload_url);
      webApp.close?.();
      return;
    }

    window.open(room.photo_upload_url, "_blank", "noopener,noreferrer");
  }

  function sendPostcardToChat(memory: RoomMemory) {
    const username = room?.photo_upload_url
      ?.match(/https:\/\/t\.me\/([^?]+)/)?.[1]
      ?.replace(/^@/, "");
    if (!username) {
      if (memory.postcard_url) {
        window.open(memory.postcard_url, "_blank", "noopener,noreferrer");
      }
      return;
    }

    const deepLink = `https://t.me/${username}?start=download_memory_${memory.id}`;
    if (webApp?.openTelegramLink) {
      webApp.openTelegramLink(deepLink);
      webApp.close?.();
      return;
    }

    window.open(deepLink, "_blank", "noopener,noreferrer");
  }

  async function revealMatch() {
    if (!token || !roomId || matchRevealed) {
      return;
    }

    setMatchRevealed(true);
    try {
      const nextRoom = await api<Room>(`/rooms/${roomId}/reveal`, token, {
        method: "POST",
        body: JSON.stringify({}),
      });
      setRoom(nextRoom);
    } catch {
      await refreshRoom();
    }
  }

  const isCurrentUserCreator =
    room?.participants.some((participant) => participant.user_id === currentTelegramUserId && participant.is_creator) ?? false;

  useEffect(() => {
    if (!token || !roomId || room?.status === "matched") {
      return;
    }

    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    let shouldReconnect = true;
    const socket = new WebSocket(`${protocol}//${window.location.host}/rooms/ws/${roomId}?token=${encodeURIComponent(token)}`);

    socket.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data) as { type?: string };
        if (payload.type === "room_updated") {
          void refreshRoom();
        }
      } catch {
        void refreshRoom();
      }
    };

    socket.onclose = () => {
      if (!shouldReconnect) {
        return;
      }
      window.setTimeout(() => {
        setSocketVersion((value) => value + 1);
      }, 2000);
    };

    return () => {
      shouldReconnect = false;
      socket.close();
    };
  }, [room?.status, roomId, token, socketVersion]);

  useEffect(() => {
    const matchedIdeaId = swipeState?.matched_idea?.id ?? room?.matched_idea?.id ?? null;
    if (!matchedIdeaId) {
      celebratedMatchRef.current = null;
      setShowMatchBurst(false);
      return;
    }

    const celebrationKey = `${roomId}:${matchedIdeaId}`;
    if (celebratedMatchRef.current === celebrationKey) {
      return;
    }

    celebratedMatchRef.current = celebrationKey;
    setShowMatchBurst(true);
    webApp?.HapticFeedback?.notificationOccurred("success");
    webApp?.HapticFeedback?.impactOccurred("heavy");
    playMatchSound();
    window.setTimeout(() => {
      setShowMatchBurst(false);
    }, 1800);
  }, [room?.matched_idea?.id, roomId, swipeState?.matched_idea?.id, webApp]);

  useEffect(() => {
    setMatchRevealed(Boolean(room?.match_revealed_at));
    setOpenedMemory(null);
  }, [roomId, room?.match_revealed_at, room?.matched_idea?.id, swipeState?.matched_idea?.id]);

  useEffect(() => {
    if (!galleryOpen) {
      return;
    }
    setGalleryOwnerFilter("all");
    setGalleryIdeaFilter("all");
    setGallerySort("newest");
  }, [galleryOpen]);

  async function startRoom() {
    if (!token || !roomId) {
      return;
    }

    setBusy(true);
    try {
      const nextRoom = await api<Room>(`/rooms/${roomId}/start`, token, {
        method: "POST",
        body: JSON.stringify({}),
      });
      setRoom(nextRoom);
      const next = await api<SwipeState>(`/rooms/${roomId}/ideas/next`, token);
      setSwipeState(next);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Не удалось начать выбор");
    } finally {
      setBusy(false);
    }
  }

  async function swipe(liked: boolean) {
    if (!token || !roomId || !swipeState?.next_idea) {
      return;
    }

    setBusy(true);
    try {
      const next = await api<SwipeState>(`/rooms/${roomId}/swipes`, token, {
        method: "POST",
        body: JSON.stringify({ idea_id: swipeState.next_idea.id, liked }),
      });
      setSwipeState(next);
      await refreshRoom();
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Не удалось отправить выбор");
    } finally {
      setBusy(false);
    }
  }

  if (loading) {
    return (
      <main className="shell shell--loading">
        <section className="glass-panel glass-panel--centered">
          <div className="loading-star">
            <IconSpark />
          </div>
          <p className="eyebrow">Подготавливаем комнату</p>
          <h1>Загружаем атмосферу...</h1>
        </section>
      </main>
    );
  }

  if (error && !roomId) {
    return (
      <main className="shell shell--loading">
        <section className="glass-panel glass-panel--centered glass-panel--error">
          <p className="eyebrow">Что-то пошло не так</p>
          <h1>Ошибка загрузки</h1>
          <p>{error}</p>
        </section>
      </main>
    );
  }

  if (!roomId) {
    return (
      <main className="shell shell--compact">
        <header className="hero">
          <p className="hero__tag">Это ОНО</p>
          <h1>Создай комнату и выбери идею для свидания.</h1>
          <p>Здесь можно начать новую комнату или вернуться к тем, где вы уже ждали, выбирали или нашли мэтч.</p>
        </header>
        <section className="glass-panel home-panel">
          <div className="actions actions--stacked">
            <button className="action action--launch" disabled={busy} onClick={() => void createRoom()}>
              <span className="action__svg"><IconSpark /></span>
              <span>{busy ? "Создаём комнату..." : "Создать комнату"}</span>
            </button>
            {globalGalleryMemories.length ? (
              <button className="action action--ghost" onClick={() => setGalleryOpen(true)}>
                <span className="action__svg"><IconGallery /></span>
                <span>Галерея</span>
              </button>
            ) : null}
          </div>
        </section>
        <section className="glass-panel home-panel">
          <div className="section-head">
            <div>
              <p className="eyebrow">Активные</p>
              <h2>Текущие комнаты</h2>
            </div>
            <span className="status-chip">
              <IconUsers />
              <span>{rooms?.active.length ?? 0}</span>
            </span>
          </div>
          <div className="room-list">
            {rooms?.active.length ? (
              rooms.active.map((activeRoom, index) => (
                <HomeRoomCard
                  key={activeRoom.id}
                  room={activeRoom}
                  title={`Комната ${index + 1}`}
                  subtitle={activeRoom.status === "waiting" ? "Ждёт второго человека" : "Выбор уже идёт"}
                  onOpen={openRoom}
                />
              ))
            ) : (
              <div className="empty-state">
                <p>Пока нет активных комнат. Создай первую прямо здесь.</p>
              </div>
            )}
          </div>
        </section>
        <section className="glass-panel home-panel">
          <div className="section-head">
            <div>
              <p className="eyebrow">Завершённые</p>
              <h2>Прошлые мэтчи</h2>
            </div>
            <span className="status-chip">
              <IconHeart />
              <span>{rooms?.completed.length ?? 0}</span>
            </span>
          </div>
          <div className="room-list">
            {rooms?.completed.length ? (
              rooms.completed.map((completedRoom) => (
                <HomeRoomCard
                  key={completedRoom.id}
                  room={completedRoom}
                  title={completedRoom.matched_idea?.title ?? "Идея для свидания"}
                  subtitle={`Мэтч от ${formatMatchDate(completedRoom.matched_at ?? completedRoom.updated_at)}`}
                  onOpen={openRoom}
                />
              ))
            ) : (
              <div className="empty-state">
                <p>Когда у вас случится мэтч, завершённая комната появится здесь.</p>
              </div>
            )}
          </div>
        </section>
        {galleryOpen ? (
          <div className="memory-modal memory-modal--gallery" onClick={() => setGalleryOpen(false)}>
            <div className="memory-modal__dialog memory-modal__dialog--gallery" onClick={(event) => event.stopPropagation()}>
              <div className="memory-modal__meta">
                <div>
                  <strong>Галерея</strong>
                  <p>Все общие фото из ваших завершённых мэтчей.</p>
                </div>
              </div>
              <div className="gallery-filters">
                <div className="gallery-filter-group">
                  <button className={`filter-chip${galleryOwnerFilter === "all" ? " filter-chip--active" : ""}`} onClick={() => setGalleryOwnerFilter("all")}>Все</button>
                  <button className={`filter-chip${galleryOwnerFilter === "mine" ? " filter-chip--active" : ""}`} onClick={() => setGalleryOwnerFilter("mine")}>Мои</button>
                  <button className={`filter-chip${galleryOwnerFilter === "partner" ? " filter-chip--active" : ""}`} onClick={() => setGalleryOwnerFilter("partner")}>Партнёра</button>
                </div>
                <div className="gallery-filter-row">
                  <label className="gallery-select">
                    <span>Идея</span>
                    <select value={galleryIdeaFilter} onChange={(event) => setGalleryIdeaFilter(event.target.value)}>
                      <option value="all">Все идеи</option>
                      {galleryIdeaOptions.map((ideaTitle) => (
                        <option key={ideaTitle} value={ideaTitle}>{ideaTitle}</option>
                      ))}
                    </select>
                  </label>
                  <label className="gallery-select">
                    <span>Дата</span>
                    <select value={gallerySort} onChange={(event) => setGallerySort(event.target.value as GallerySort)}>
                      <option value="newest">Сначала новые</option>
                      <option value="oldest">Сначала старые</option>
                    </select>
                  </label>
                </div>
              </div>
              {filteredGalleryMemories.length ? (
                <div className="gallery-grid">
                  {filteredGalleryMemories.map((memory) => (
                    <button
                      key={`${memory.room_id}-${memory.id}`}
                      className="gallery-card"
                      onClick={() => {
                        setGalleryOpen(false);
                        setOpenedMemory(memory);
                      }}
                    >
                      <img className="gallery-card__image" src={memory.photo_url ?? ""} alt={`Фото от ${memory.uploaded_by_name}`} />
                      <div className="gallery-card__meta">
                        <strong>{memory.idea_title}</strong>
                        <span>{memory.uploaded_by_name}</span>
                        <span>{formatMatchDate(memory.created_at)}</span>
                      </div>
                    </button>
                  ))}
                </div>
              ) : (
                <div className="empty-state">
                  <p>По выбранным фильтрам пока ничего не нашлось.</p>
                </div>
              )}
            </div>
          </div>
        ) : null}
        {openedMemory?.postcard_url ? (
          <div className="memory-modal" onClick={() => setOpenedMemory(null)}>
            <div className="memory-modal__dialog" onClick={(event) => event.stopPropagation()}>
              <img
                className="memory-modal__image"
                src={openedMemory.photo_url ?? openedMemory.postcard_url}
                alt={`Фото от ${openedMemory.uploaded_by_name}`}
              />
              <div className="memory-modal__meta">
                <div>
                  <strong>{openedMemory.uploaded_by_name}</strong>
                  <p>{formatMatchDate(openedMemory.created_at)}</p>
                </div>
                <div className="memory-modal__actions">
                  <button className="action action--launch" onClick={() => sendPostcardToChat(openedMemory)}>
                    <span className="action__svg"><IconSpark /></span>
                    <span>Отправить открытку в чат</span>
                  </button>
                </div>
              </div>
            </div>
          </div>
        ) : null}
      </main>
    );
  }

  if (error && !room) {
    return (
      <main className="shell shell--loading">
        <section className="glass-panel glass-panel--centered glass-panel--error">
          <p className="eyebrow">Что-то пошло не так</p>
          <h1>Ошибка загрузки</h1>
          <p>{error}</p>
        </section>
      </main>
    );
  }

  if (!room) {
    return null;
  }

  if (room.status === "matched" || swipeState?.matched) {
    const idea = swipeState?.matched_idea ?? room.matched_idea;
    if (!idea) {
      return null;
    }

    return (
      <main className="shell shell--match shell--compact">
        {showMatchBurst ? <MatchBurst /> : null}
        <header className="hero hero--match">
          <p className="hero__tag">Раскрытие</p>
          <h1>Сотри вашу общую идею</h1>
          <p>Вы оба выбрали одно и то же. Сотри слой и открой ваше свидание.</p>
        </header>
        <ScratchReveal
          idea={idea}
          initiallyRevealed={Boolean(room.match_revealed_at)}
          onReveal={() => void revealMatch()}
        />
        {matchRevealed ? (
          <>
            <div className="actions actions--stacked">
              {room.photo_upload_url ? (
                <button className="action action--launch" onClick={openPhotoUploadFlow}>
                  <span className="action__svg"><IconShare /></span>
                  <span>{room.photo_uploaded ? "Добавить ещё фото свидания" : "Добавить фото свидания"}</span>
                </button>
              ) : null}
            </div>
            <section className="glass-panel memory-panel">
              <div className="section-head">
                <div>
                  <p className="eyebrow">Воспоминания</p>
                  <h2>Открытки из этой комнаты</h2>
                </div>
                <span className="status-chip">
                  <IconSpark />
                  <span>{room.memories.length}</span>
                </span>
              </div>
              {room.memories.length ? (
                <div className="memory-list">
                  {room.memories.map((memory) => (
                    <article className="memory-card" key={memory.id}>
                      <div className="memory-card__head">
                        <strong>{memory.uploaded_by_name}</strong>
                        <span>{formatMatchDate(memory.created_at)}</span>
                      </div>
                      <p>Фото свидания, добавленное в комнату.</p>
                      <MemoryPreview memory={memory} onOpen={setOpenedMemory} />
                    </article>
                  ))}
                </div>
              ) : (
                <div className="empty-state">
                  <p>Пока нет загруженных фото. После раскрытия любой участник может добавить свои снимки в чат с ботом.</p>
                </div>
              )}
            </section>
          </>
        ) : null}
        {openedMemory?.postcard_url ? (
          <div className="memory-modal" onClick={() => setOpenedMemory(null)}>
            <div className="memory-modal__dialog" onClick={(event) => event.stopPropagation()}>
              <img className="memory-modal__image" src={openedMemory.postcard_url} alt={`Открытка от ${openedMemory.uploaded_by_name}`} />
              <div className="memory-modal__meta">
                <div>
                  <strong>{openedMemory.uploaded_by_name}</strong>
                  <p>{formatMatchDate(openedMemory.created_at)}</p>
                </div>
                <div className="memory-modal__actions">
                  {openedMemory.photo_url ? (
                    <a className="action action--ghost" href={openedMemory.photo_url} target="_blank" rel="noreferrer">
                      <span className="action__svg"><IconIdea /></span>
                      <span>Исходное фото</span>
                    </a>
                  ) : null}
                  <button className="action action--launch" onClick={() => sendPostcardToChat(openedMemory)}>
                    <span className="action__svg"><IconSpark /></span>
                    <span>Отправить в чат файлом</span>
                  </button>
                </div>
              </div>
            </div>
          </div>
        ) : null}
        {galleryOpen ? (
          <div className="memory-modal memory-modal--gallery" onClick={() => setGalleryOpen(false)}>
            <div className="memory-modal__dialog memory-modal__dialog--gallery" onClick={(event) => event.stopPropagation()}>
              <div className="memory-modal__meta">
                <div>
                  <strong>Галерея</strong>
                  <p>Все общие фото из ваших завершённых мэтчей.</p>
                </div>
              </div>
              <div className="gallery-filters">
                <div className="gallery-filter-group">
                  <button className={`filter-chip${galleryOwnerFilter === "all" ? " filter-chip--active" : ""}`} onClick={() => setGalleryOwnerFilter("all")}>Все</button>
                  <button className={`filter-chip${galleryOwnerFilter === "mine" ? " filter-chip--active" : ""}`} onClick={() => setGalleryOwnerFilter("mine")}>Мои</button>
                  <button className={`filter-chip${galleryOwnerFilter === "partner" ? " filter-chip--active" : ""}`} onClick={() => setGalleryOwnerFilter("partner")}>Партнёра</button>
                </div>
                <div className="gallery-filter-row">
                  <label className="gallery-select">
                    <span>Идея</span>
                    <select value={galleryIdeaFilter} onChange={(event) => setGalleryIdeaFilter(event.target.value)}>
                      <option value="all">Все идеи</option>
                      {galleryIdeaOptions.map((ideaTitle) => (
                        <option key={ideaTitle} value={ideaTitle}>{ideaTitle}</option>
                      ))}
                    </select>
                  </label>
                  <label className="gallery-select">
                    <span>Дата</span>
                    <select value={gallerySort} onChange={(event) => setGallerySort(event.target.value as GallerySort)}>
                      <option value="newest">Сначала новые</option>
                      <option value="oldest">Сначала старые</option>
                    </select>
                  </label>
                </div>
              </div>
              {filteredGalleryMemories.length ? (
                <div className="gallery-grid">
                  {filteredGalleryMemories.map((memory) => (
                    <button
                      key={`${memory.room_id}-${memory.id}`}
                      className="gallery-card"
                      onClick={() => {
                        setGalleryOpen(false);
                        setOpenedMemory(memory);
                      }}
                    >
                      <img className="gallery-card__image" src={memory.photo_url ?? ""} alt={`Фото от ${memory.uploaded_by_name}`} />
                      <div className="gallery-card__meta">
                        <strong>{memory.idea_title}</strong>
                        <span>{memory.uploaded_by_name}</span>
                        <span>{formatMatchDate(memory.created_at)}</span>
                      </div>
                    </button>
                  ))}
                </div>
              ) : (
                <div className="empty-state">
                  <p>По выбранным фильтрам пока ничего не нашлось.</p>
                </div>
              )}
            </div>
          </div>
        ) : null}
      </main>
    );
  }

  if (room.status === "waiting") {
    return (
      <main className="shell shell--compact">
        <header className="hero">
          <p className="hero__tag">Комната</p>
          <h1>Выберите свидание, в которое хочется пойти.</h1>
          <p>Одна общая комната, уютная атмосфера и идеи, которые могут совпасть у вас обоих.</p>
        </header>
        <section className="glass-panel lobby-panel">
          <div className="lobby-panel__halo lobby-panel__halo--left" />
          <div className="lobby-panel__halo lobby-panel__halo--right" />
          <div className="section-head section-head--top">
            <span className={`room-badge room-badge--${room.status}`}>{statusLabel(room.status)}</span>
          </div>
          <div className="lobby-head">
            <div>
              <p className="eyebrow">Участники</p>
              <h2>{room.participants_count}/{room.max_participants}</h2>
            </div>
            <div className="status-chip">
              <IconUsers />
              <span>{room.participants_count < room.max_participants ? "Ждём второго человека" : "Можно начинать"}</span>
            </div>
          </div>
          <p className="lobby-copy">Пригласи человека через Telegram, а дальше комната обновится сама в реальном времени.</p>
          <button className="action action--share" onClick={shareInviteLink}>
            <span className="action__svg"><IconShare /></span>
            <span>Пригласить в Telegram</span>
          </button>
          <div className="participants-grid">
            {room.participants.map((participant) => (
              <div key={participant.user_id} className="participant-card">
                <div className="participant-card__avatar">{participant.name.slice(0, 1)}</div>
                <div className="participant-card__text">
                  <strong>{participant.name}</strong>
                  <span>{participant.is_creator ? "Создатель" : "Партнёр"}</span>
                </div>
              </div>
            ))}
          </div>
          {room.can_start && isCurrentUserCreator ? (
            <button className="action action--launch" disabled={busy} onClick={() => void startRoom()}>
              <span className="action__svg"><IconSpark /></span>
              <span>{busy ? "Открываем колоду..." : "Начать выбор"}</span>
            </button>
          ) : (
            <div className="waiting-banner">
              <span className="waiting-banner__pulse" />
              <span>
                {room.participants_count < room.max_participants
                  ? "Ждём, пока второй человек войдёт в комнату."
                  : "Только создатель комнаты может начать выбор."}
              </span>
            </div>
          )}
        </section>
      </main>
    );
  }

  const idea = swipeState?.next_idea;
  if (!idea) {
    return (
      <main className="shell shell--loading">
        <section className="glass-panel glass-panel--centered">
          <p className="eyebrow">Колода закончилась</p>
          <h1>Пока больше нет карточек</h1>
          <p>Можно обновить комнату позже или добавить новые идеи в базу.</p>
        </section>
      </main>
    );
  }

  return (
    <main className="shell shell--deck shell--compact">
      <header className="hero hero--deck">
        <p className="hero__tag">Выбор</p>
        <h1>Выбери, что откликается.</h1>
        <p>Вправо, если нравится. Влево, если нет.</p>
      </header>
      <SwipeCard busy={busy} idea={idea} onSwipe={(liked) => void swipe(liked)} />
    </main>
  );
}

export default App;
