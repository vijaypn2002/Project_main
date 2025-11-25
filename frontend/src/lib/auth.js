// token storage
const TOKEN_KEY = "jwt_access";
const USER_EMAIL_KEY = "user_email";

export const auth = {
  access() {
    return localStorage.getItem(TOKEN_KEY) || null;
  },
  set(tokens) {
    // expect { access, refresh } from backend token endpoint
    if (tokens?.access) localStorage.setItem(TOKEN_KEY, tokens.access);
  },
  clear() {
    localStorage.removeItem(TOKEN_KEY);
  },
};

// tiny helper for email we display on Orders/Returns
export const currentUser = {
  get email() {
    return localStorage.getItem(USER_EMAIL_KEY) || "";
  },
  set email(v) {
    if (v) localStorage.setItem(USER_EMAIL_KEY, v);
  },
};
