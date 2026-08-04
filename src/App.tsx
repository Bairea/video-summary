import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import Home from "@/pages/Home";
import AppLayout from "@/components/AppLayout";
import TaskDetail from "@/pages/TaskDetail";
import Settings from "@/pages/Settings";

export default function App() {
  return (
    <Router>
      <Routes>
        <Route element={<AppLayout />}>
          <Route path="/" element={<Home />} />
          <Route path="/task/:id" element={<TaskDetail />} />
          <Route path="/settings" element={<Settings />} />
        </Route>
      </Routes>
    </Router>
  );
}
