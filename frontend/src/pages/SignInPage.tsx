import { useState } from "react";
import { GoogleAuthProvider, signInWithEmailAndPassword, signInWithPopup } from "firebase/auth";
import { firebaseAuth, firebaseConfigured } from "../lib/firebase";

export default function SignInPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [message, setMessage] = useState("");
  async function emailSignIn() {
    setMessage("");
    if (!firebaseAuth) return setMessage("Configure Firebase web settings in frontend/.env first.");
    try { await signInWithEmailAndPassword(firebaseAuth, email, password); setMessage("Signed in."); }
    catch (e) { setMessage(e instanceof Error ? e.message : "Sign-in failed."); }
  }
  async function googleSignIn() {
    setMessage("");
    if (!firebaseAuth) return setMessage("Configure Firebase web settings in frontend/.env first.");
    try { await signInWithPopup(firebaseAuth, new GoogleAuthProvider()); setMessage("Signed in."); }
    catch (e) { setMessage(e instanceof Error ? e.message : "Google sign-in failed."); }
  }
  return <div className="signin-wrap"><div className="panel signin-card"><div className="brand-mark">O</div><h1>Sign in to ObliGOT</h1><p>Use your configured Firebase Authentication provider.</p>{!firebaseConfigured&&<div className="notice">Firebase is not configured yet. The demo UI can still run without sign-in while developing locally.</div>}<label>Email<input className="search-input" value={email} onChange={e=>setEmail(e.target.value)} type="email" autoComplete="email"/></label><label>Password<input className="search-input" value={password} onChange={e=>setPassword(e.target.value)} type="password" autoComplete="current-password"/></label><button className="button button-primary" onClick={()=>void emailSignIn()}>Sign in with email</button><button className="button button-secondary" onClick={()=>void googleSignIn()}>Continue with Google</button>{message&&<p className="signin-message">{message}</p>}</div></div>;
}
