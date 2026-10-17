import { useEffect, useState, type ReactNode } from "react";
import { Navigate, useLocation } from "react-router-dom";
import { onAuthStateChanged, type User } from "firebase/auth";
import { firebaseAuth, firebaseConfigured } from "./firebase";

/** Current Firebase user; `ready` turns true once Firebase has restored (or ruled out) a session. */
export function useAuthUser(): { user: User | null; ready: boolean } {
  const [state, setState] = useState<{ user: User | null; ready: boolean }>({ user: firebaseAuth?.currentUser ?? null, ready: !firebaseAuth });
  useEffect(() => {
    if (!firebaseAuth) return;
    return onAuthStateChanged(firebaseAuth, (user) => setState({ user, ready: true }));
  }, []);
  return state;
}

/** Workspace routes need a signed-in user whenever Firebase is configured. Without Firebase web settings
 * (local development only) the workspace stays open, and the backend decides whether tokens are required. */
export function RequireAuth({ children }: { children: ReactNode }) {
  const { user, ready } = useAuthUser();
  const location = useLocation();
  if (!firebaseConfigured) return <>{children}</>;
  if (!ready) return <p className="api-state" role="status">Checking your sign-in…</p>;
  if (!user) return <Navigate to={`/auth?next=${encodeURIComponent(location.pathname + location.search)}`} replace />;
  return <>{children}</>;
}

/** Readable messages for Firebase Auth error codes; never shows raw provider errors. */
export function authErrorMessage(error: unknown): string {
  const code = error && typeof error === "object" && "code" in error ? String((error as { code: unknown }).code) : "";
  switch (code) {
    case "auth/invalid-credential": case "auth/wrong-password": case "auth/user-not-found": case "auth/invalid-login-credentials":
      return "Email or password is incorrect.";
    case "auth/invalid-email": return "Enter a valid email address.";
    case "auth/email-already-in-use": return "An account with this email already exists. Sign in instead.";
    case "auth/weak-password": return "Use a password with at least 6 characters.";
    case "auth/too-many-requests": return "Too many attempts. Wait a moment and try again.";
    case "auth/network-request-failed": return "Network error. Check your connection and try again.";
    case "auth/operation-not-allowed": return "This sign-in method is not enabled in Firebase (Authentication › Sign-in method).";
    case "auth/unauthorized-domain": return "This domain is not authorized in Firebase. Add it under Authentication › Settings › Authorized domains.";
    default: return "Sign-in failed. Please try again.";
  }
}
