export enum APIErrorCode {
  INVALID_URL = 1001,
  INVALID_RESPONSE = 1002,
  DECODING_ERROR = 1003,
  SERVER_ERROR = 1004,
  UNAUTHORIZED = 401,
  NETWORK_ERROR = 1006
}

export class APIError {
  code: number;
  message: string;

  constructor(code: number, message: string) {
    this.code = code;
    this.message = message;
  }
}
