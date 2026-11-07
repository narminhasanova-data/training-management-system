// A small inline icon set (24×24 strokes), so the app needs no icon dependency.
const PATHS = {
  agenda: "M8 3v3M16 3v3M4 9h16M5 5h14a1 1 0 0 1 1 1v13a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V6a1 1 0 0 1 1-1Zm3 8h3m-3 4h6",
  survey: "M9 4h6a1 1 0 0 1 1 1v1H8V5a1 1 0 0 1 1-1ZM8 5H6a1 1 0 0 0-1 1v14a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1V6a1 1 0 0 0-1-1h-2M9 12l2 2 4-4M9 17h6",
  tracker: "M4 5h16v14H4zM4 10h16M9 5v14M14 5v14",
  classroom: "M3 10 12 5l9 5-9 5-9-5Zm4 2.2V16c0 1.2 2.2 3 5 3s5-1.8 5-3v-3.8M21 10v5",
  checklist: "M9 6h11M9 12h11M9 18h11M4 6l1 1 2-2M4 12l1 1 2-2M4 18l1 1 2-2",
  reports: "M5 20V10M12 20V4M19 20v-7",
  logout: "M15 4h3a1 1 0 0 1 1 1v14a1 1 0 0 1-1 1h-3M10 16l-4-4 4-4M6 12h10",
  menu: "M4 7h16M4 12h16M4 17h16",
  x: "M6 6l12 12M18 6 6 18",
  plus: "M12 5v14M5 12h14",
  trash: "M5 7h14M10 7V5h4v2M7 7l1 12h8l1-12",
  download: "M12 4v11m-4-4 4 4 4-4M5 19h14",
  mail: "M4 6h16v12H4zM4 7l8 6 8-6",
  phone: "M7 4h3l1.5 4-2 1.5a10 10 0 0 0 5 5l1.5-2L20 14v3a2 2 0 0 1-2 2A15 15 0 0 1 5 6a2 2 0 0 1 2-2Z",
  refresh: "M20 11a8 8 0 0 0-14.6-4.5M4 4v4h4M4 13a8 8 0 0 0 14.6 4.5M20 20v-4h-4",
  eye: "M2 12s3.6-7 10-7 10 7 10 7-3.6 7-10 7S2 12 2 12Zm10 3a3 3 0 1 0 0-6 3 3 0 0 0 0 6Z",
  check: "M5 12.5 10 17 19 7",
  clock: "M12 7v5l3 2m6-2a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z",
  alert: "M12 8v5m0 3.5v.5M10.3 4.3 2.6 18a2 2 0 0 0 1.7 3h15.4a2 2 0 0 0 1.7-3L13.7 4.3a2 2 0 0 0-3.4 0Z",
  chevron: "m9 6 6 6-6 6",
  search: "m20 20-4.5-4.5M17 11a6 6 0 1 1-12 0 6 6 0 0 1 12 0Z",
  file: "M7 3h7l5 5v13H7zM14 3v5h5",
  link: "M10 14a4 4 0 0 0 5.7 0l3-3a4 4 0 0 0-5.7-5.7l-1 1M14 10a4 4 0 0 0-5.7 0l-3 3a4 4 0 0 0 5.7 5.7l1-1",
  video: "M4 6h11v12H4zM15 10l5-3v10l-5-3",
  send: "M4 12 20 4l-6 16-3-7-7-1Z",
  users: "M9 11a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7Zm-6 9a6 6 0 0 1 12 0M16 4.5a3.5 3.5 0 0 1 0 6.5M21 20a6 6 0 0 0-4-5.6",
  copy: "M9 9h10v10H9zM5 15V5h10",
};

export default function Icon({ name, size = 18, className = "" }) {
  return (
    <svg
      className={`icon ${className}`}
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d={PATHS[name] || PATHS.file} />
    </svg>
  );
}
