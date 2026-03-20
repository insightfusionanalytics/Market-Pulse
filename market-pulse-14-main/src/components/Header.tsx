import React from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { clearToken } from "@/lib/api";
import { LogOut } from "lucide-react";

interface HeaderProps {
  connected: boolean;
  currentTime: string;
}

const Header: React.FC<HeaderProps> = ({ connected, currentTime }) => {
  const navigate = useNavigate();

  const handleLogout = () => {
    clearToken();
    navigate("/");
  };

  return (
    <header className="sticky top-0 z-50 flex items-center justify-between border-b border-border bg-card px-6 py-3">
      <h1 className="text-xl font-bold text-primary tracking-wide">
        NSE Pre-Open Scanner
      </h1>

      <span className="text-lg font-mono text-muted-foreground">
        {currentTime} IST
      </span>

      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2 text-sm">
          <span
            className={`inline-block h-2.5 w-2.5 rounded-full ${
              connected ? "bg-success" : "bg-destructive"
            }`}
          />
          <span className={connected ? "text-success" : "text-destructive"}>
            {connected ? "Connected" : "Disconnected"}
          </span>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={handleLogout}
          className="border-border text-muted-foreground hover:text-foreground hover:bg-secondary"
        >
          <LogOut className="h-4 w-4 mr-1" />
          Logout
        </Button>
      </div>
    </header>
  );
};

export default Header;
