export function readStoredUser() {
  try {
    const userJson = localStorage.getItem('edu_user');
    if (!userJson) return {};
    const parsed = JSON.parse(userJson);
    return parsed && typeof parsed === 'object' ? parsed : {};
  } catch (_) {
    return {};
  }
}

export function isStoredAdmin() {
  return readStoredUser().is_admin === true;
}
