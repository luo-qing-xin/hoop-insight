import { Outlet, useLocation } from "react-router-dom";
import Layout from "./components/Layout";
import { GAME_DETAIL_COPY, PAGE_COPY } from "./constants/zhLabels";

function getPageCopy(pathname: string) {
  if (pathname.startsWith("/games/")) {
    return GAME_DETAIL_COPY;
  }

  return PAGE_COPY[pathname] ?? PAGE_COPY["/"];
}

export default function App() {
  const location = useLocation();
  const page = getPageCopy(location.pathname);
  const layoutClassName = location.pathname === "/data-center" ? "layout-data-center" : "";

  return (
    <Layout title={page.title} eyebrow={page.eyebrow} description={page.description} className={layoutClassName}>
      <Outlet />
    </Layout>
  );
}
