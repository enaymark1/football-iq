import { lazy, Suspense } from "react";
import { Route, Routes } from "react-router-dom";
import { Loading } from "./components/ui";
import AppLayout from "./layouts/AppLayout";

// Cada página se descarga recién cuando se visita.
const OverviewPage = lazy(() => import("./pages/OverviewPage"));
const PlayersPage = lazy(() => import("./pages/PlayersPage"));
const PlayerProfilePage = lazy(() => import("./pages/PlayerProfilePage"));
const ComparePage = lazy(() => import("./pages/ComparePage"));
const ScoutingPage = lazy(() => import("./pages/ScoutingPage"));
const SimilarPage = lazy(() => import("./pages/SimilarPage"));
const MarketPage = lazy(() => import("./pages/MarketPage"));
const MatchPredictorPage = lazy(() => import("./pages/MatchPredictorPage"));
const TeamsPage = lazy(() => import("./pages/TeamsPage"));
const TeamDetailPage = lazy(() => import("./pages/TeamDetailPage"));
const ModelsPage = lazy(() => import("./pages/ModelsPage"));
const NotFoundPage = lazy(() => import("./pages/NotFoundPage"));

export default function App() {
  return (
    <Suspense fallback={<Loading />}>
      <Routes>
        <Route element={<AppLayout />}>
          <Route index element={<OverviewPage />} />
          <Route path="players" element={<PlayersPage />} />
          <Route path="players/:id" element={<PlayerProfilePage />} />
          <Route path="compare" element={<ComparePage />} />
          <Route path="scouting" element={<ScoutingPage />} />
          <Route path="similar" element={<SimilarPage />} />
          <Route path="market" element={<MarketPage />} />
          <Route path="match-predictor" element={<MatchPredictorPage />} />
          <Route path="teams" element={<TeamsPage />} />
          <Route path="teams/:id" element={<TeamDetailPage />} />
          <Route path="models" element={<ModelsPage />} />
          <Route path="*" element={<NotFoundPage />} />
        </Route>
      </Routes>
    </Suspense>
  );
}
