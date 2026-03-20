import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { login, setToken } from "@/lib/api";
import { Loader2 } from "lucide-react";

const Login: React.FC = () => {
  const navigate = useNavigate();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const response = await login({ username, password });
      setToken(response.access_token);
      navigate("/dashboard");
    } catch (err: any) {
      setError(err.message || "Unable to connect to server");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-background to-secondary px-4">
      <Card className="w-full max-w-md border-border bg-card">
        <CardHeader className="text-center">
          <CardTitle className="text-3xl font-bold text-primary">
            NSE Pre-Open Scanner
          </CardTitle>
          <p className="text-sm text-muted-foreground mt-1">
            Real-time pre-open market data
          </p>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="username" className="text-muted-foreground">Username</Label>
              <Input
                id="username"
                placeholder="Username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                className="bg-secondary border-border text-foreground placeholder:text-muted-foreground"
                autoComplete="username"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="password" className="text-muted-foreground">Password</Label>
              <Input
                id="password"
                type="password"
                placeholder="Password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="bg-secondary border-border text-foreground placeholder:text-muted-foreground"
                autoComplete="current-password"
              />
            </div>
            {error && (
              <p className="text-sm text-destructive text-center">{error}</p>
            )}
            <Button
              type="submit"
              className="w-full bg-primary text-primary-foreground hover:bg-primary/80 font-semibold"
              disabled={loading || !username || !password}
            >
              {loading ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Logging in...
                </>
              ) : (
                "Login"
              )}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
};

export default Login;
