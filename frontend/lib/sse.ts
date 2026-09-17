// Minimal text/event-stream parser (WHATWG SSE: event/data fields, blank line ends an event).
// Pure and framework-free so it can be checked with plain node.

export type SseMessage = { event: string; data: string };

/** Feed decoded text chunks with `push`; complete events go to `onMessage`. Call `end` when the stream closes. */
export function createSseParser(onMessage: (message: SseMessage) => void) {
  let buffer = "";
  let event = "";
  let data: string[] = [];

  const dispatch = () => {
    if (data.length) onMessage({ event: event || "message", data: data.join("\n") });
    event = "";
    data = [];
  };

  const line = (text: string) => {
    if (text === "") return dispatch();
    if (text.startsWith(":")) return; // comment / keep-alive
    const colon = text.indexOf(":");
    const field = colon === -1 ? text : text.slice(0, colon);
    let value = colon === -1 ? "" : text.slice(colon + 1);
    if (value.startsWith(" ")) value = value.slice(1);
    if (field === "event") event = value;
    else if (field === "data") data.push(value);
  };

  return {
    push(chunk: string) {
      buffer += chunk;
      let match: RegExpExecArray | null;
      const newline = /\r\n|\r|\n/g;
      let start = 0;
      while ((match = newline.exec(buffer))) {
        // A trailing "\r" may be the first half of "\r\n": wait for the next chunk.
        if (match[0] === "\r" && match.index === buffer.length - 1) break;
        line(buffer.slice(start, match.index));
        start = match.index + match[0].length;
      }
      buffer = buffer.slice(start);
    },
    /** Stream closed. Per spec an event without its terminating blank line is discarded. */
    end() {
      buffer = "";
      event = "";
      data = [];
    },
  };
}
