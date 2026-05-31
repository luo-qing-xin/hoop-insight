import React from "react";
import ReactDOM from "react-dom/client";
import { Navigate, RouterProvider, createBrowserRouter } from "react-router-dom";
import App from "./App";
import "./styles/globals.css";

const router = createBrowserRouter([
  {
    path: "/",
    element: <App />,
    children: [
      { index: true, lazy: () => import("./pages/Dashboard") },
      { path: "games", lazy: () => import("./pages/Games") },
      { path: "games/:gameId", lazy: () => import("./pages/GameDetail") },
      { path: "players", lazy: () => import("./pages/Players") },
      { path: "teams", lazy: () => import("./pages/Teams") },
      { path: "shots", lazy: () => import("./pages/Shots") },
      { path: "data-center", lazy: () => import("./pages/DataCenter") },
      { path: "ask-ai", lazy: () => import("./pages/AskAI") },
      { path: "*", element: <Navigate to="/" replace /> },
    ],
  },
]);

ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(
  <React.StrictMode>
    <RouterProvider router={router} />
  </React.StrictMode>,
);
