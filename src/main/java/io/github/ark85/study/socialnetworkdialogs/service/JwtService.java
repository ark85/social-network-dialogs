package io.github.ark85.study.socialnetworkdialogs.service;

import io.github.ark85.study.socialnetworkdialogs.configuration.JwtProperties;
import io.jsonwebtoken.Claims;
import io.jsonwebtoken.Jws;
import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.io.Decoders;
import io.jsonwebtoken.security.Keys;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import javax.crypto.SecretKey;
import java.time.Instant;
import java.util.Date;

@Service
@Slf4j
public class JwtService {

    private final SecretKey secretKey;

    public JwtService(JwtProperties jwtProperties) {
        this.secretKey = Keys.hmacShaKeyFor(Decoders.BASE64.decode(jwtProperties.getSecret()));
    }

    public Jws<Claims> parseToken(String token) {
        return Jwts.parser().verifyWith(secretKey).build().parseSignedClaims(token);
    }

    public boolean isJwtValid(Claims claims) {
        return claims.getExpiration().after(Date.from(Instant.now()));
    }
}
