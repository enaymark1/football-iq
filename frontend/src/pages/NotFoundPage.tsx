import { Link } from "react-router-dom";
import { Card, EmptyState } from "../components/ui";

export default function NotFoundPage() {
  return (
    <Card>
      <EmptyState title="Página no encontrada">
        <Link to="/" className="text-accent hover:underline">Volver al Overview</Link>
      </EmptyState>
    </Card>
  );
}
