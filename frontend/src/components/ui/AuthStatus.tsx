import { useEffect, useState } from "react";
import { onAuthStateChanged, signOut, type User } from "firebase/auth";
import { firebaseAuth, firebaseConfigured } from "../../lib/firebase";

export default function AuthStatus() {
  const [user, setUser] = useState<User | null>(null);
  useEffect(() => {
    if (!firebaseAuth) return;
    return onAuthStateChanged(firebaseAuth, setUser);
  }, []);
  if (!firebaseConfigured) return <span className="auth-note">Firebase not configured</span>;
  if (!user) return <span className="auth-note">Signed out</span>;
  return <button className="auth-button" onClick={() => void signOut(firebaseAuth!)} title="Sign out">{user.email || "Signed in"} · Sign out</button>;
}
