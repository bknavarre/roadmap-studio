import { initializeApp } from 'firebase/app';
import { getFirestore, doc, onSnapshot, setDoc, serverTimestamp } from 'firebase/firestore';
import {
  getAuth,
  setPersistence,
  browserLocalPersistence,
  signInWithEmailAndPassword,
  signOut as firebaseSignOut,
  onAuthStateChanged,
} from 'firebase/auth';

// SIS Roadmap Studio Firebase web app configuration.
// These values identify the project; access is controlled by Firebase Authentication.
const firebaseConfig = {
  apiKey: 'AIzaSyBupAhajrgIqoLwhWxIHQm2KPsbOeRsslY',
  authDomain: 'sis-roadmap-studio.firebaseapp.com',
  projectId: 'sis-roadmap-studio',
  storageBucket: 'sis-roadmap-studio.firebasestorage.app',
  messagingSenderId: '169145233958',
  appId: '1:169145233958:web:f27f092f3f7cc6c1fb2ce7',
};

const app = initializeApp(firebaseConfig);
export const auth = getAuth(app);
export const db = getFirestore(app);
export const enableLocalAuth = () => setPersistence(auth, browserLocalPersistence);
export const loginWithEmail = (email, password) => signInWithEmailAndPassword(auth, email, password);
export const logout = () => firebaseSignOut(auth);
export { onAuthStateChanged };

export { doc, onSnapshot, setDoc, serverTimestamp };
