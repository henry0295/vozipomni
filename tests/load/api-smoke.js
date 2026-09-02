import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  vus: Number(__ENV.VUS || 10),
  duration: __ENV.DURATION || '1m',
  thresholds: { http_req_failed: ['rate<0.01'], http_req_duration: ['p(95)<500'] },
};

const baseUrl = __ENV.BASE_URL || 'https://localhost';

export default function () {
  const response = http.get(`${baseUrl}/api/health/`, { tags: { endpoint: 'health' } });
  check(response, { 'health responds': (res) => res.status === 200 });
  sleep(1);
}