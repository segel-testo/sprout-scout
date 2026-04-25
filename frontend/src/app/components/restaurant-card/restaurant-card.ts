import { Component, Input } from '@angular/core';
import { Restaurant, ScanResult } from '../../services/restaurant';

interface PrimaryLink {
  label: string;
  url: string;
}

@Component({
  selector: 'app-restaurant-card',
  imports: [],
  templateUrl: './restaurant-card.html',
  styleUrl: './restaurant-card.scss',
})
export class RestaurantCard {
  @Input() restaurant!: Restaurant;
  @Input() scan!: ScanResult;

  get primaryLink(): PrimaryLink {
    const dl = this.scan?.delivery_link;
    if (dl) return { label: dl.label, url: dl.url };
    if (this.restaurant.website) {
      return { label: 'Visit website', url: this.restaurant.website };
    }
    const query = encodeURIComponent(`${this.restaurant.name} ${this.restaurant.address}`.trim());
    return {
      label: 'Find on Google Maps',
      url: `https://www.google.com/maps/search/?api=1&query=${query}`,
    };
  }
}
