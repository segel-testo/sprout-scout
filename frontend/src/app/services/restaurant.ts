import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';

export interface Restaurant {
  id: string;
  name: string;
  address: string;
  website: string;
  phone: string;
  amenity?: string | null;
}

export interface DeliveryLink {
  platform: string;
  url: string;
  label: string;
}

export interface ScanResult {
  restaurant_id: string;
  delivery_link?: DeliveryLink | null;
}

export type ScanEvent =
  | { type: 'start'; total: number; total_available: number; capped: boolean }
  | { type: 'restaurant'; restaurant: Restaurant; scan: ScanResult }
  | { type: 'progress'; scanned: number; total: number }
  | { type: 'error'; restaurant_id: string; reason: string }
  | { type: 'done'; scanned: number; total: number };

@Injectable({ providedIn: 'root' })
export class RestaurantService {
  private apiUrl = environment.apiUrl;

  scanStream(zipCode: string, amenity?: string): Observable<ScanEvent> {
    const params = new URLSearchParams({ zip_code: zipCode, country: 'AT' });
    if (amenity) params.set('amenity', amenity);
    return this.streamFrom(`${this.apiUrl}/restaurants/scan?${params.toString()}`);
  }

  scanStreamByRadius(lat: number, lon: number, radius: number, amenity?: string): Observable<ScanEvent> {
    const params = new URLSearchParams({
      lat: String(lat),
      lon: String(lon),
      radius: String(radius),
    });
    if (amenity) params.set('amenity', amenity);
    return this.streamFrom(`${this.apiUrl}/restaurants/scan-by-radius?${params.toString()}`);
  }

  private streamFrom(url: string): Observable<ScanEvent> {
    return new Observable<ScanEvent>((subscriber) => {
      const source = new EventSource(url);
      let received = false;

      const forward = (type: ScanEvent['type']) => (ev: MessageEvent) => {
        received = true;
        try {
          const data = JSON.parse(ev.data);
          subscriber.next({ type, ...data } as ScanEvent);
          if (type === 'done') {
            source.close();
            subscriber.complete();
          }
        } catch (e) {
          subscriber.error(e);
        }
      };

      source.addEventListener('start', forward('start') as EventListener);
      source.addEventListener('restaurant', forward('restaurant') as EventListener);
      source.addEventListener('progress', forward('progress') as EventListener);
      source.addEventListener('error', forward('error') as EventListener);
      source.addEventListener('done', forward('done') as EventListener);

      source.onerror = () => {
        if (source.readyState === EventSource.CLOSED) {
          if (received) {
            subscriber.complete();
          } else {
            subscriber.error(new Error('connection-failed'));
          }
        }
      };

      return () => source.close();
    });
  }
}
