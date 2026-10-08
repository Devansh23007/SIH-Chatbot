import { useCallback, useEffect, useRef, useState, type KeyboardEvent, type PointerEvent } from 'react';

export interface Size { w: number; h: number }

const MIN: Size = { w: 340, h: 420 };
const EXPANDED_WIDTH = 760;
const KEY_STEP = 24;
const EDGE_GAP = 40; // 20px offset on each side of the viewport

const clamp = ({ w, h }: Size): Size => ({
  w: Math.min(Math.max(w, MIN.w), Math.max(MIN.w, window.innerWidth - EDGE_GAP)),
  h: Math.min(Math.max(h, MIN.h), Math.max(MIN.h, window.innerHeight - EDGE_GAP)),
});

/**
 * Desktop resizing for a window anchored to the bottom-right corner, so the drag handle sits at the
 * top-left: dragging up/left makes it bigger. `size === null` means "use the default size".
 * State lives in the widget so the size survives minimize.
 */
export function useResizableWindow() {
  const [size, setSize] = useState<Size | null>(null);
  const [expanded, setExpanded] = useState(false);
  const windowRef = useRef<HTMLElement | null>(null);

  const current = useCallback((): Size | null => {
    const rect = windowRef.current?.getBoundingClientRect();
    return rect ? { w: rect.width, h: rect.height } : null;
  }, []);

  const startResize = useCallback((e: PointerEvent<HTMLButtonElement>) => {
    const start = current();
    if (!start) return;
    e.preventDefault();
    const handle = e.currentTarget;
    const { clientX: x0, clientY: y0 } = e;
    handle.setPointerCapture(e.pointerId);

    const onMove = (ev: globalThis.PointerEvent) => {
      setExpanded(false);
      setSize(clamp({ w: start.w + (x0 - ev.clientX), h: start.h + (y0 - ev.clientY) }));
    };
    const onEnd = () => {
      handle.removeEventListener('pointermove', onMove);
      handle.removeEventListener('pointerup', onEnd);
      handle.removeEventListener('pointercancel', onEnd);
    };
    handle.addEventListener('pointermove', onMove);
    handle.addEventListener('pointerup', onEnd);
    handle.addEventListener('pointercancel', onEnd);
  }, [current]);

  // Keyboard alternative: arrows on the focused handle (Left/Up grow, Right/Down shrink).
  const onHandleKeyDown = useCallback((e: KeyboardEvent<HTMLButtonElement>) => {
    const deltas: Record<string, [number, number]> = {
      ArrowLeft: [KEY_STEP, 0], ArrowRight: [-KEY_STEP, 0], ArrowUp: [0, KEY_STEP], ArrowDown: [0, -KEY_STEP],
    };
    const d = deltas[e.key];
    const start = current();
    if (!d || !start) return;
    e.preventDefault();
    setExpanded(false);
    setSize(clamp({ w: start.w + d[0], h: start.h + d[1] }));
  }, [current]);

  const toggleExpand = useCallback(() => {
    if (expanded) { setSize(null); setExpanded(false); }
    else { setSize(clamp({ w: EXPANDED_WIDTH, h: window.innerHeight })); setExpanded(true); }
  }, [expanded]);

  // Keep the window inside the viewport when the browser window shrinks.
  useEffect(() => {
    const onResize = () => setSize((s) => (s ? clamp(s) : s));
    window.addEventListener('resize', onResize);
    return () => window.removeEventListener('resize', onResize);
  }, []);

  return { size, expanded, windowRef, startResize, onHandleKeyDown, toggleExpand };
}

export type ResizableWindow = ReturnType<typeof useResizableWindow>;
